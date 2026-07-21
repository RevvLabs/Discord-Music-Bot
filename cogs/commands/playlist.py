import asyncio
import discord
import voltricx
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.unified_cache_manager import unified_cache
from utils.helper_function.ratelimit import LAVALINK_SEARCH_SEM
from utils.helper_function.spotify_scraper import scrape_spotify_playlist
from utils.helper_function.bot_config import EMBED_COLOR
from utils.logger.mewzik_logger import bot_logger
from utils.embed_designs import playlist as pl_design
from emojis import PREV_BTN, NEXT_BTN

load_dotenv()

_ALLOWED_DOMAINS = ("open.spotify.com", "spotify.com", "youtube.com", "youtu.be", "music.youtube.com")
_PLAYLIST_SEGMENTS = ("/playlist/", "/album/", "list=")


def _is_valid_playlist_link(url: str) -> bool:
    u = url.lower()
    return any(d in u for d in _ALLOWED_DOMAINS) and any(s in u for s in _PLAYLIST_SEGMENTS)


def _is_spotify(url: str) -> bool:
    return "spotify" in url.lower()

_MAX_SONGS = 100
_PAGE_SIZE = 10
_PLAYLIST_TARGET = 5  # keep this many tracks queued at all times; rest trickles in as songs finish

# guild_id -> {"remaining": list[(title, author, requestor, engine)]}
# Songs carry their own requestor/engine so sessions from different users/playlists
# can be safely merged instead of clobbering each other.
_playlist_sessions: dict[int, dict] = {}


def has_playlist_session(guild_id: int) -> bool:
    return guild_id in _playlist_sessions


def get_playlist_session(guild_id: int) -> dict | None:
    return _playlist_sessions.get(guild_id)


def stop_playlist_session(guild_id: int) -> None:
    _playlist_sessions.pop(guild_id, None)


def advance_playlist_session(guild_id: int, count: int) -> list:
    """Pop up to `count` songs off the pending queue for top-up. Clears session when exhausted."""
    session = _playlist_sessions.get(guild_id)
    if not session:
        return []
    batch, session["remaining"] = session["remaining"][:count], session["remaining"][count:]
    if not session["remaining"]:
        _playlist_sessions.pop(guild_id, None)
    return batch


def _fmt_song(title: str, author: str) -> str:
    """Format 'Title - Artist', truncated to 30 characters."""
    label = f"{title} - {author}" if author else title
    return (label[:29] + "…") if len(label) > 30 else label


# ── Voice helper ──────────────────────────────────────────────────────────────

async def _ensure_voice(ctx: commands.Context, interaction: discord.Interaction = None) -> "LavaMusic | None":
    """Join or validate voice for playback. Returns player or None on failure."""
    send = interaction.followup.send if interaction else ctx.send
    user = interaction.user if interaction else ctx.author
    guild = interaction.guild if interaction else ctx.guild

    if not user.voice or not user.voice.channel:
        await send(view=pl_design.voice_required(), ephemeral=True)
        return None

    vc = guild.voice_client
    if not vc:
        try:
            player: LavaMusic = await user.voice.channel.connect(
                cls=LavaMusic, timeout=45, reconnect=True, self_deaf=True
            )
            return player
        except Exception:
            await send(view=pl_design.join_failed(), ephemeral=True)
            return None
    elif vc.channel != user.voice.channel:
        await send(view=pl_design.different_voice(), ephemeral=True)
        return None
    return vc


# ── Playback helper ───────────────────────────────────────────────────────────

async def _resolve_one(query: str, user_engine: str):
    """Search for a single track across sources. Returns track or None."""
    for source in [user_engine, "ytsearch", "dzsearch"]:
        try:
            async with LAVALINK_SEARCH_SEM:
                results = await voltricx.Playable.search(query, source=source)
            if results:
                return results.tracks[0] if isinstance(results, voltricx.Playlist) else results[0]
        except Exception:
            continue
    return None


async def _start_playlist_playback(
    songs: list,
    player: LavaMusic,
    requestor: discord.Member,
    user_engine: str,
) -> str | None:
    """
    Cold start (nothing playing, no session running): resolve+play the first
    track immediately, fill the rest of the initial _PLAYLIST_TARGET batch in
    the background, register the tail as a session that trickles in one-by-one
    as tracks end (see on_voltricx_track_end).

    Hot path (something's already playing, or another playlist is already
    trickling in): don't front-load a new batch — that would burst extra
    search requests and blow past _PLAYLIST_TARGET. Instead just append this
    playlist's songs onto the existing/new session tail so it plays out after
    whatever's already queued, merging cleanly with a concurrent user's "Play
    All" instead of discarding it.

    Returns "started", "queued", or None if nothing resolved / nothing to do.
    """
    if not songs:
        return None

    guild_id = player.guild.id
    tagged = [(title, author, requestor, user_engine) for _, title, author in songs]

    # Claim/merge the session SYNCHRONOUSLY — before any `await` — so a second
    # concurrent "Play All" always observes this one and merges its songs onto
    # the tail instead of racing into its own cold start and clobbering us.
    cold = not player.playing and not has_playlist_session(guild_id)
    session = _playlist_sessions.setdefault(guild_id, {"remaining": []})

    if not cold:
        session["remaining"].extend(tagged)
        return "queued"

    # Cold start: front-load the first batch directly into the queue, park the
    # rest of the playlist on the session tail (extend, not assign — a racing
    # caller may already have merged songs here during our awaits below).
    batch = tagged[:_PLAYLIST_TARGET]
    session["remaining"].extend(tagged[_PLAYLIST_TARGET:])

    # Phase 1: find and play the first resolvable track in the batch
    batch_iter = iter(batch)
    first_queued = False
    for title, author, req, eng in batch_iter:
        t = await _resolve_one(f"{title} {author}".strip(), eng)
        if t:
            player.metadata[t] = {"requestor": req, "source": t.source}
            player.queue.put(t)
            first_queued = True
            break

    if not first_queued:
        # Whole batch unresolvable (backend likely down). Drop the reservation
        # so it can't wedge a later play_all into permanent "queued" limbo with
        # nothing playing to drive the top-up.
        _playlist_sessions.pop(guild_id, None)
        return None

    try:
        next_track = player.queue.get()
        await player.play(next_track, replace=False)
    except Exception:
        pass

    # Phase 2: resolve the rest of the initial batch (up to target) in the background
    rest_of_batch = list(batch_iter)

    async def _bg_fill_batch():
        for title, author, req, eng in rest_of_batch:
            if not player.check_queue_size():
                break
            t = await _resolve_one(f"{title} {author}".strip(), eng)
            if t:
                player.metadata[t] = {"requestor": req, "source": t.source}
                player.queue.put(t)
            await asyncio.sleep(0.3)

    if rest_of_batch:
        asyncio.create_task(_bg_fill_batch())

    # Phase 3: if nothing was parked on the tail, drop the empty reservation so
    # a later play_all cold-starts cleanly instead of appending into limbo.
    if not session["remaining"]:
        _playlist_sessions.pop(guild_id, None)

    return "started"


# ── Import helper ────────────────────────────────────────────────────────────

async def _import_songs_from_link(
    url: str,
    playlist_id: int,
    user_id: int,
    slots: int,
) -> tuple[int, int]:
    """
    Scrape `url` and save up to `slots` songs into the playlist.
    Returns (added, skipped) counts.
    """
    added = skipped = 0

    if _is_spotify(url):
        clean = url.split("?")[0]
        sp_result = await scrape_spotify_playlist(clean)
        if not sp_result or not sp_result.track_pairs:
            return 0, 0
        for title, artist in sp_result.track_pairs[:slots]:
            result = await unified_cache.add_song_to_playlist(playlist_id, user_id, title, artist)
            if result == "ok":
                added += 1
            elif result == "duplicate":
                skipped += 1
            elif result == "full":
                break
            await asyncio.sleep(0.1)
    else:
        # YouTube / generic URL
        try:
            results = await voltricx.Playable.search(url)
        except Exception:
            return 0, 0
        if not results:
            return 0, 0
        track_list = results.tracks if isinstance(results, voltricx.Playlist) else results
        for track in track_list[:slots]:
            title = track.title or ""
            author = getattr(track, "author", "") or ""
            result = await unified_cache.add_song_to_playlist(playlist_id, user_id, title, author)
            if result == "ok":
                added += 1
            elif result == "duplicate":
                skipped += 1
            elif result == "full":
                break
            await asyncio.sleep(0.1)

    return added, skipped


# ── Modal: create playlist ────────────────────────────────────────────────────

class CreatePlaylistModal(discord.ui.Modal, title="Create Playlist"):
    pl_name = discord.ui.TextInput(
        label="Playlist Name",
        placeholder="e.g. Chill Vibes",
        max_length=50,
        required=True,
    )

    def __init__(self, list_view: "PlaylistListView"):
        super().__init__()
        self._list_view = list_view

    async def on_submit(self, interaction: discord.Interaction):
        name = self.pl_name.value.strip()
        ok = await unified_cache.create_user_playlist(interaction.user.id, name)
        if not ok:
            await interaction.response.send_message(
                view=pl_design.playlist_name_taken(name), ephemeral=True
            )
            return
        await interaction.response.defer()
        await self._list_view.reload(interaction)


# ── Modal: import from link ───────────────────────────────────────────────────

class ImportLinkModal(discord.ui.Modal, title="Import Playlist from Link"):
    pl_link = discord.ui.TextInput(
        label="YouTube or Spotify Playlist Link",
        placeholder="https://open.spotify.com/playlist/... or youtube.com/playlist?list=...",
        max_length=500,
        required=True,
    )

    def __init__(self, detail_view: "PlaylistDetailView"):
        super().__init__()
        self._detail = detail_view

    async def on_submit(self, interaction: discord.Interaction):
        url = self.pl_link.value.strip()
        if not _is_valid_playlist_link(url):
            await interaction.response.send_message(
                "Only **YouTube** and **Spotify** playlist/album links are supported.",
                ephemeral=True,
            )
            return

        current_count = len(self._detail.songs)
        slots = _MAX_SONGS - current_count
        if slots <= 0:
            await interaction.response.send_message(
                view=pl_design.playlist_full(), ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Importing songs from link… (up to **{slots}** slots remaining)", ephemeral=True
        )

        added, skipped = await _import_songs_from_link(
            url, self._detail.playlist_id, interaction.user.id, slots
        )

        summary = f"Import done — **{added}** song(s) added"
        if skipped:
            summary += f", **{skipped}** duplicate(s) skipped"
        summary += "."
        try:
            await interaction.followup.send(summary, ephemeral=True)
        except Exception:
            pass

        await self._detail.reload_songs(interaction)


# ── Select: open a playlist detail ───────────────────────────────────────────

class OpenPlaylistSelect(discord.ui.Select):
    def __init__(self, playlists: list, list_view: "PlaylistListView"):
        options = [
            discord.SelectOption(
                label=name[:90],
                value=str(pl_id),
                description=f"{song_count} song(s)",
            )
            for pl_id, name, song_count in playlists[:25]
        ]
        super().__init__(placeholder="Open a playlist…", min_values=1, max_values=1, options=options)
        self._map = {str(pl_id): name for pl_id, name, _ in playlists}
        self._list_view = list_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self._list_view.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        pl_id = int(self.values[0])
        name = self._map[self.values[0]]
        detail = PlaylistDetailView(
            author_id=self._list_view.author_id,
            playlist_id=pl_id,
            playlist_name=name,
            ctx=self._list_view.ctx,
        )
        await detail.load_songs()
        await interaction.response.edit_message(view=detail)
        detail.message = self._list_view.message


# ── Select: delete a playlist ─────────────────────────────────────────────────

class DeletePlaylistSelect(discord.ui.Select):
    def __init__(self, playlists: list, list_view: "PlaylistListView"):
        options = [
            discord.SelectOption(label=name[:90], value=str(pl_id))
            for pl_id, name, _ in playlists[:25]
        ]
        super().__init__(placeholder="Delete a playlist…", min_values=1, max_values=1, options=options)
        self._map = {str(pl_id): name for pl_id, name, _ in playlists}
        self._list_view = list_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self._list_view.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        pl_id = int(self.values[0])
        name = self._map[self.values[0]]
        ok = await unified_cache.remove_user_playlist(interaction.user.id, pl_id)
        if ok:
            await interaction.response.send_message(view=pl_design.playlist_deleted(name), ephemeral=True)
        else:
            await interaction.response.send_message(view=pl_design.save_failed(), ephemeral=True)
        await self._list_view.reload(interaction)


# ── Playlist list view ────────────────────────────────────────────────────────

class PlaylistListView(discord.ui.LayoutView):
    def __init__(self, author_id: int, playlists: list, ctx: commands.Context):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.playlists = playlists
        self.ctx = ctx
        self.message: discord.Message | None = None
        self._build()

    def _build(self):
        self.clear_items()
        has = bool(self.playlists)

        if has:
            lines = "\n".join(
                f"**{i+1}. {name}** — {cnt} song(s)"
                for i, (_, name, cnt) in enumerate(self.playlists)
            )
            body = f"You have **{len(self.playlists)}** playlist(s).\n\n{lines}"
        else:
            body = "You have no playlists yet.\nClick **＋ Create** to make one!"

        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 🎵 My Playlists"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=body),
            accent_color=EMBED_COLOR,
        )
        self.add_item(container)

        btn_row = discord.ui.ActionRow()
        create_btn = discord.ui.Button(label="＋ Create", style=discord.ButtonStyle.success)
        close_btn = discord.ui.Button(label="✕ Close", style=discord.ButtonStyle.danger)
        create_btn.callback = self._create_callback
        close_btn.callback = self._close_callback
        btn_row.add_item(create_btn)
        btn_row.add_item(close_btn)
        self.add_item(btn_row)

        if has:
            open_row = discord.ui.ActionRow()
            open_row.add_item(OpenPlaylistSelect(self.playlists, self))
            self.add_item(open_row)

            del_row = discord.ui.ActionRow()
            del_row.add_item(DeletePlaylistSelect(self.playlists, self))
            self.add_item(del_row)

    async def _create_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        await interaction.response.send_modal(CreatePlaylistModal(self))

    async def _close_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        try:
            await interaction.message.delete()
        except Exception:
            await interaction.response.defer()

    async def reload(self, interaction: discord.Interaction):
        self.playlists = await unified_cache.get_user_playlists(self.author_id)
        self._build()
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass

    async def on_timeout(self):
        if self.message:
            try:
                v = discord.ui.LayoutView()
                v.add_item(discord.ui.Container(
                    discord.ui.TextDisplay(content="⏳ Closed — inactive for too long."),
                    accent_color=discord.Color.from_rgb(128, 128, 128),
                ))
                await self.message.edit(view=v)
            except Exception:
                pass


# ── Select: remove songs from current page ────────────────────────────────────

class RemoveSongsSelect(discord.ui.Select):
    def __init__(self, page_songs: list, detail_view: "PlaylistDetailView"):
        options = [
            discord.SelectOption(label=_fmt_song(title, author), value=str(song_id))
            for song_id, title, author in page_songs
        ]
        super().__init__(
            placeholder="Remove songs from this page…",
            min_values=1,
            max_values=len(page_songs),
            options=options,
        )
        self._detail = detail_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self._detail.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        ids = [int(v) for v in self.values]
        ok = await unified_cache.remove_songs_from_playlist(
            self._detail.playlist_id, interaction.user.id, ids
        )
        if ok:
            await interaction.response.send_message(
                view=pl_design.songs_removed(len(ids)), ephemeral=True
            )
        else:
            await interaction.response.send_message(view=pl_design.save_failed(), ephemeral=True)
        await self._detail.reload_songs(interaction)


# ── Playlist detail view ──────────────────────────────────────────────────────

class PlaylistDetailView(discord.ui.LayoutView):
    def __init__(
        self,
        author_id: int,
        playlist_id: int,
        playlist_name: str,
        ctx: commands.Context,
    ):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.playlist_id = playlist_id
        self.playlist_name = playlist_name
        self.ctx = ctx
        self.message: discord.Message | None = None
        self.songs: list = []
        self.current_page = 0

    @property
    def _pages(self) -> list:
        return [self.songs[i:i + _PAGE_SIZE] for i in range(0, max(1, len(self.songs)), _PAGE_SIZE)]

    async def load_songs(self):
        self.songs = await unified_cache.get_playlist_songs(self.playlist_id)
        self._build()

    async def reload_songs(self, interaction: discord.Interaction):
        self.songs = await unified_cache.get_playlist_songs(self.playlist_id)
        pages = self._pages
        if self.current_page >= len(pages):
            self.current_page = max(0, len(pages) - 1)
        self._build()
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass

    def _build(self):
        self.clear_items()
        pages = self._pages
        page = pages[self.current_page] if pages else []
        total_pages = len(pages)

        if self.songs:
            offset = self.current_page * _PAGE_SIZE
            lines = "\n".join(
                f"**{offset + i + 1}.** {_fmt_song(title, author)}"
                for i, (_, title, author) in enumerate(page)
            )
            body = f"{lines}\n\n*Page {self.current_page + 1}/{total_pages} · {len(self.songs)}/{_MAX_SONGS} songs*"
        else:
            body = "No songs yet. Add some using **＋ Add Current Song**."

        container = discord.ui.Container(
            discord.ui.TextDisplay(content=f"## 📋 {self.playlist_name}"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=body),
            accent_color=EMBED_COLOR,
        )
        self.add_item(container)

        # Navigation row
        nav_row = discord.ui.ActionRow()
        prev_btn = discord.ui.Button(
            label="Previous",
            emoji=PREV_BTN,
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page <= 0,
        )
        next_btn = discord.ui.Button(
            label="Next",
            emoji=NEXT_BTN,
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page >= total_pages - 1,
        )
        prev_btn.callback = self._prev_page
        next_btn.callback = self._next_page
        nav_row.add_item(prev_btn)
        nav_row.add_item(next_btn)
        self.add_item(nav_row)

        # Action row
        action_row = discord.ui.ActionRow()
        play_btn = discord.ui.Button(
            label="▶ Play All",
            style=discord.ButtonStyle.success,
            disabled=not self.songs,
        )
        add_btn = discord.ui.Button(
            label="＋ Add Current Song",
            style=discord.ButtonStyle.primary,
            disabled=len(self.songs) >= _MAX_SONGS,
        )
        import_btn = discord.ui.Button(
            label="📥 Import from Link",
            style=discord.ButtonStyle.secondary,
            disabled=len(self.songs) >= _MAX_SONGS,
        )
        play_btn.callback = self._play_all
        add_btn.callback = self._add_current
        import_btn.callback = self._import_link
        action_row.add_item(play_btn)
        action_row.add_item(add_btn)
        action_row.add_item(import_btn)
        self.add_item(action_row)

        # Remove / Back row
        if page:
            remove_row = discord.ui.ActionRow()
            remove_row.add_item(RemoveSongsSelect(page, self))
            self.add_item(remove_row)

        back_row = discord.ui.ActionRow()
        back_btn = discord.ui.Button(label="← Back", style=discord.ButtonStyle.secondary)
        close_btn = discord.ui.Button(label="✕ Close", style=discord.ButtonStyle.danger)
        back_btn.callback = self._go_back
        close_btn.callback = self._close_callback
        back_row.add_item(back_btn)
        back_row.add_item(close_btn)
        self.add_item(back_row)

    async def _prev_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        self.current_page -= 1
        self._build()
        await interaction.response.edit_message(view=self)

    async def _next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        self.current_page += 1
        self._build()
        await interaction.response.edit_message(view=self)

    async def _add_current(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return

        player: LavaMusic = interaction.guild.voice_client
        if not player or not player.current:
            await interaction.response.send_message(view=pl_design.nothing_playing(), ephemeral=True)
            return

        title = player.current.title or ""
        author = getattr(player.current, "author", "") or ""

        result = await unified_cache.add_song_to_playlist(
            self.playlist_id, interaction.user.id, title, author
        )

        if result == "ok":
            await interaction.response.send_message(
                view=pl_design.song_added(title, author, self.playlist_name), ephemeral=True
            )
            await self.reload_songs(interaction)
        elif result == "duplicate":
            await interaction.response.send_message(
                view=pl_design.song_already_in_playlist(), ephemeral=True
            )
        elif result == "full":
            await interaction.response.send_message(view=pl_design.playlist_full(), ephemeral=True)
        else:
            await interaction.response.send_message(view=pl_design.save_failed(), ephemeral=True)

    async def _import_link(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        await interaction.response.send_modal(ImportLinkModal(self))

    async def _play_all(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        if not self.songs:
            await interaction.response.send_message(view=pl_design.no_songs_to_play(), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        player = await _ensure_voice(self.ctx, interaction)
        if not player:
            return

        if not isinstance(player.queue, voltricx.Queue):
            player.queue = voltricx.Queue()
        if not getattr(player, "home", None):
            player.home = self.ctx.channel

        user_engine = await unified_cache.get_user_engine(interaction.user.id) or "ytsearch"
        if not await unified_cache.is_engine_enabled(user_engine):
            user_engine = "ytsearch"

        # Mutually exclusive with autoplay — kill any lingering autoplay session
        # for this guild so it can't reactivate later and inject stale tracks.
        from utils.helper_function.autoplay_cache import autoplay_cache
        autoplay_cache.stop_session(interaction.guild.id)

        songs = await unified_cache.get_playlist_songs(self.playlist_id)
        outcome = await _start_playlist_playback(songs, player, interaction.user, user_engine)

        if not outcome:
            await interaction.followup.send(view=pl_design.no_songs_to_play(), ephemeral=True)
            return

        if outcome == "queued":
            msg = f"➕ Queued **{self.playlist_name}** ({len(songs)} song(s)) behind current playback."
        else:
            remaining = len(songs) - 1
            msg = f"▶ Started **{self.playlist_name}**!"
            if remaining > 0:
                msg += f" Loading **{remaining}** more song(s) in the background…"
        await interaction.followup.send(msg, ephemeral=True)

        if bot_logger.enabled:
            await bot_logger.async_incoming(
                "playlist — play all",
                playlist=self.playlist_name,
                total=len(songs),
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
            )

    async def _go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        playlists = await unified_cache.get_user_playlists(self.author_id)
        list_view = PlaylistListView(self.author_id, playlists, self.ctx)
        list_view.message = self.message
        await interaction.response.edit_message(view=list_view)

    async def _close_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the invoker can use this.", ephemeral=True)
            return
        try:
            await interaction.message.delete()
        except Exception:
            await interaction.response.defer()

    async def on_timeout(self):
        if self.message:
            try:
                v = discord.ui.LayoutView()
                v.add_item(discord.ui.Container(
                    discord.ui.TextDisplay(content="⏳ Closed — inactive for too long."),
                    accent_color=discord.Color.from_rgb(128, 128, 128),
                ))
                await self.message.edit(view=v)
            except Exception:
                pass


# ── Cog ───────────────────────────────────────────────────────────────────────

class Playlist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="playlist",
        description="Manage your playlists — create, add songs, and play them.",
        aliases=["pl"],
    )
    @commands.cooldown(1, 5, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def playlist(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if ctx.interaction:
            await ctx.defer(ephemeral=True)

        playlists = await unified_cache.get_user_playlists(ctx.author.id)
        view = PlaylistListView(ctx.author.id, playlists, ctx)
        msg = await ctx.send(view=view, ephemeral=True)
        view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(Playlist(bot))
