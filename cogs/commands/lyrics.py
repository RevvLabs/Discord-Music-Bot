import asyncio
import re
import time
import aiohttp
import discord
from unidecode import unidecode
from discord.ext import commands
from discord.ext.commands import BucketType

import voltricx
from emojis import PREV_BTN, NEXT_BTN
from utils.colours.colours import ORANGE, RESET
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.voice_connected import ensure_voice
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs.lyrics import lyrics_container, lyrics_not_found, nothing_playing, searching

_CHUNK_SIZE = 3800  # Components v2 caps total message text at 4000; leave room for title + page counter
_LRCLIB_BASE = "https://lrclib.net/api"
# Upper bound only — lrclib is often slow (multi-second) and sometimes 502s,
# so a tight per-read timeout makes valid lyrics fail. 15s caps a true hang
# without cutting off slow-but-working responses. Cache keeps repeats instant.
_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=15)
# Cache resolved lyrics in-memory so repeat lookups are instant.
_CACHE_TTL = 3600  # seconds
_CACHE_MAX = 256
_TIMESTAMP = re.compile(r'^\[\d+:\d+\.\d+\]\s?', re.MULTILINE)
_PARENS = re.compile(r'\s*[\(\[【][^\)\]】]*[\)\]】]', re.IGNORECASE)
_PIPE   = re.compile(r'\s*[|].*$')
_FT     = re.compile(r'\s+(?:ft|feat)\..*$', re.IGNORECASE)
_YT_SOURCES = {"youtube", "youtubemusic"}


def _search_title(title: str) -> str:
    """Strip YouTube noise for lrclib search. Keeps dash-separated parts intact."""
    t = _PARENS.sub('', title)
    t = _PIPE.sub('', t)
    return _FT.sub('', t).strip()


def _extract_lyrics(item: dict) -> str | None:
    plain = item.get("plainLyrics")
    if plain and plain.strip():
        return plain.strip()
    synced = item.get("syncedLyrics")
    if synced and synced.strip():
        return _TIMESTAMP.sub('', synced).strip()
    return None


def _title_score(searched: str, found: str) -> int:
    """Score how well `found` matches `searched`. Higher = better."""
    s = searched.lower().strip()
    f = found.lower().strip()
    if s == f:
        return 4
    if s in f or f in s:
        return 3
    s_words = [w for w in re.split(r'\W+', s) if len(w) > 1]
    f_words = set(re.split(r'\W+', f))
    matched = sum(1 for w in s_words if w in f_words)
    if matched == len(s_words) and s_words:
        return 2
    if matched > 0:
        return 1
    return 0


def _title_match(searched: str, found: str) -> bool:
    return _title_score(searched, found) > 0


def _is_latin(text: str) -> bool:
    """True if text is mostly Latin/ASCII characters (romanized)."""
    if not text:
        return False
    non_space = [c for c in text if not c.isspace()]
    if not non_space:
        return False
    latin = sum(1 for c in non_space if ord(c) < 256)
    return latin / len(non_space) > 0.75


def _to_hinglish(text: str) -> str:
    """Transliterate non-Latin lyrics to Roman script."""
    if _is_latin(text):
        return text
    return unidecode(text)


class LyricsPaginationView(discord.ui.LayoutView):
    def __init__(self, chunks: list[str], title: str, ctx: commands.Context, persistent: bool = False):
        # persistent=True → no auto-timeout; the view lives until the song ends
        # (the Lyrics cog deletes it on track end / inactivity).
        super().__init__(timeout=None if persistent else 60)
        self.chunks = chunks
        self.title = title
        self.ctx = ctx
        self.current_page = 0
        self.message: discord.Message | None = None

        self._prev_btn = discord.ui.Button(label="Previous", emoji=PREV_BTN, style=discord.ButtonStyle.secondary)
        self._next_btn = discord.ui.Button(label="Next", emoji=NEXT_BTN, style=discord.ButtonStyle.secondary)
        self._prev_btn.callback = self._prev
        self._next_btn.callback = self._next

        self._rebuild()

    def _rebuild(self):
        self._prev_btn.disabled = self.current_page <= 0
        self._next_btn.disabled = self.current_page >= len(self.chunks) - 1
        self.clear_items()
        row = discord.ui.ActionRow()
        row.add_item(self._prev_btn)
        row.add_item(self._next_btn)
        self.add_item(lyrics_container(self.title, self.chunks[self.current_page], self.current_page, len(self.chunks)))
        self.add_item(row)

    async def _prev(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You cannot control this.", ephemeral=True)
            return
        self.current_page -= 1
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def _next(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You cannot control this.", ephemeral=True)
            return
        self.current_page += 1
        self._rebuild()
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=discord.ui.LayoutView())
            except Exception:
                pass


def _chunk_lyrics(text: str) -> list[str]:
    lines = text.splitlines()
    chunks, current = [], []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > _CHUNK_SIZE and current:
            chunks.append("\n".join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks or ["(empty)"]


async def _fetch_by_track(session: aiohttp.ClientSession, title: str, author: str, duration_ms: int) -> str | None:
    try:
        async with session.get(f"{_LRCLIB_BASE}/get", params={
            "track_name": title,
            "artist_name": author,
            "duration": int(duration_ms / 1000),
        }) as resp:
            if resp.status == 200:
                lyrics = _extract_lyrics(await resp.json())
                if lyrics:
                    return lyrics
    except Exception:
        pass
    return None


async def _fetch_by_query(session: aiohttp.ClientSession, query: str) -> tuple[str, str] | tuple[None, None]:
    try:
        async with session.get(f"{_LRCLIB_BASE}/search", params={"q": query}) as resp:
            if resp.status == 200:
                results = await resp.json()
                best_score = -1
                best = (None, None)
                for item in results:
                    lyrics = _extract_lyrics(item)
                    if not lyrics:
                        continue
                    name = item.get("trackName") or query
                    score = _title_score(query, name)
                    if score > best_score:
                        best_score = score
                        best = (lyrics, name)
                return best
    except Exception:
        pass
    return None, None


def _parse_lavalyrics(data: dict) -> str | None:
    text = data.get("text") or ""
    if not text:
        lines = data.get("lines") or []
        text = "\n".join(e.get("line", "") for e in lines).strip()
    return text or None


async def _lavalyrics_current(player, guild_id: int) -> str | None:
    try:
        url = f"/v4/sessions/{player.node.session_id}/players/{guild_id}/track/lyrics"
        data = await player.node.request("GET", url, params={"skipTrackSource": "false"})
        if not data:
            data = await player.node.request("GET", url, params={"skipTrackSource": "true"})
        return _parse_lavalyrics(data) if data else None
    except Exception:
        return None


async def _lavalyrics_encoded(node, encoded: str) -> str | None:
    try:
        data = await node.request("GET", "/v4/lyrics", params={"track": encoded, "skipTrackSource": "true"})
        return _parse_lavalyrics(data) if data else None
    except Exception:
        return None


async def _lrclib_for_track(
    session: aiohttp.ClientSession,
    title: str,
    author: str,
    duration_ms: int,
) -> tuple[str | None, str | None]:
    """Parallel lrclib searches using source metadata. Returns (lyrics, display_title)."""
    q = _search_title(title)   # strip YouTube noise for search
    exact, (with_author, wa_title), (title_only, to_title) = await asyncio.gather(
        _fetch_by_track(session, q, author, duration_ms),
        _fetch_by_query(session, f"{q} - {author}"),
        _fetch_by_query(session, q),
    )
    print(f"{ORANGE}[lrclib]{RESET} q={q!r} author={author!r} exact={bool(exact)} wa_title={wa_title!r} to_title={to_title!r}")
    if exact:
        return exact, q
    if with_author and wa_title and _title_match(q, wa_title):
        return with_author, wa_title
    if title_only and to_title and _title_match(q, to_title):
        return title_only, to_title
    return None, None


class Lyrics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._session: aiohttp.ClientSession | None = None
        self._cache: dict[str, tuple[str, str | None, float]] = {}
        # guild_id -> list of (message, view) for current-track lyrics still on screen.
        self._active: dict[int, list[tuple[discord.Message, "LyricsPaginationView"]]] = {}

    async def cog_load(self):
        # One keep-alive session for the cog's lifetime — avoids a fresh
        # TCP+TLS handshake to lrclib on every command.
        self._session = aiohttp.ClientSession(
            timeout=_HTTP_TIMEOUT,
            connector=aiohttp.TCPConnector(limit=20, ttl_dns_cache=300),
        )

    async def cog_unload(self):
        for entries in self._active.values():
            for _, view in entries:
                view.stop()
        self._active.clear()
        if self._session and not self._session.closed:
            await self._session.close()

    async def _clear_active(self, guild_id: int) -> None:
        """Delete + stop any current-track lyrics shown in this guild (song changed/ended)."""
        entries = self._active.pop(guild_id, None)
        if not entries:
            return
        for message, view in entries:
            view.stop()
            try:
                await message.delete()
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_voltricx_track_end(self, player, track, reason):
        if player and player.guild:
            await self._clear_active(player.guild.id)

    @commands.Cog.listener()
    async def on_voltricx_inactive_player(self, player):
        if player and player.guild:
            await self._clear_active(player.guild.id)

    def _cache_get(self, key: str) -> tuple[str, str | None] | None:
        hit = self._cache.get(key)
        if not hit:
            return None
        text, title, expiry = hit
        if time.monotonic() > expiry:
            self._cache.pop(key, None)
            return None
        return text, title

    def _cache_put(self, key: str, text: str, title: str | None) -> None:
        if len(self._cache) >= _CACHE_MAX:
            # Drop the oldest entry (dicts keep insertion order).
            self._cache.pop(next(iter(self._cache)), None)
        self._cache[key] = (text, title, time.monotonic() + _CACHE_TTL)

    @commands.hybrid_command(name="lyrics", description="Show lyrics for the current song or a search query.")
    @commands.cooldown(1, 5, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def lyrics(self, ctx: commands.Context, *, query: str = None):
        # Current-track lyrics require being in the bot's VC; explicit-query
        # lookups are read-only and allowed from anywhere.
        if not query and not await ensure_voice(ctx):
            return

        await ctx.defer()

        player: LavaMusic = ctx.guild.voice_client

        # Nothing playing and no query → no search to run.
        if not query and (not player or not player.current):
            await ctx.send(view=nothing_playing())
            return

        text = None
        display_title = query or (player.current.title if player and player.current else "this track")

        # Send a live "searching" message immediately; we edit THIS same message
        # once the lookup finishes (found → lyrics, miss → not-found).
        status_msg = await ctx.send(view=searching(display_title))

        # Build a cache key up front so repeat lookups skip the network entirely.
        if query:
            cache_key = f"q:{query.lower().strip()}"
        elif player and player.current:
            tr = player.current
            cache_key = f"t:{(tr.title or '').lower()}|{(tr.author or '').lower()}|{tr.length // 1000}"
        else:
            cache_key = None

        cached = self._cache_get(cache_key) if cache_key else None
        if cached:
            text, ctitle = cached
            if ctitle:
                display_title = ctitle

        session = self._session
        if not cached:
            try:
                if not query:
                    track = player.current
                    display_title = track.title
                    print(f"{ORANGE}[lyrics]{RESET} source={track.source!r} title={track.title!r} author={track.author!r} length={track.length} plugin_info={track.plugin_info}")
                    text, found = await _lrclib_for_track(session, track.title, track.author, track.length)
                    print(f"{ORANGE}[lyrics]{RESET} lrclib result: found={found!r} has_text={bool(text)}")
                    if found:
                        display_title = found
                    if not text:
                        text = await _lavalyrics_current(player, ctx.guild.id)
                        print(f"{ORANGE}[lyrics]{RESET} lavalyrics fallback: has_text={bool(text)}")
                else:
                    lrc_lyrics, lrc_title = await _fetch_by_query(session, query)
                    if lrc_lyrics:
                        text = lrc_lyrics
                        if lrc_title:
                            display_title = lrc_title

                    if not text and player:
                        yt_result = await player.node.load_tracks(f"ytmsearch:{query}")
                        tracks = getattr(yt_result, "tracks", None)
                        if tracks:
                            t = tracks[0]
                            display_title = t.title
                            lrc_text, lrc_found = await _lrclib_for_track(session, t.title, t.author, t.length)
                            if lrc_text:
                                text = lrc_text
                                if lrc_found:
                                    display_title = lrc_found
                            else:
                                text = await _lavalyrics_encoded(player.node, t.encoded)
            except Exception:
                pass

            # Cache positive results only.
            if cache_key and text and text.strip():
                self._cache_put(cache_key, text, display_title)

        if not text or not text.strip():
            await status_msg.edit(view=lyrics_not_found(display_title))
            return

        text = _to_hinglish(text)
        chunks = _chunk_lyrics(text)

        # Current-track lyrics (no query) are tied to the playing song: keep the
        # buttons alive with no timeout, and auto-delete when the song ends.
        track_linked = not query
        view = LyricsPaginationView(chunks, display_title, ctx, persistent=track_linked)
        await status_msg.edit(view=view)
        view.message = status_msg
        if track_linked:
            self._active.setdefault(ctx.guild.id, []).append((status_msg, view))


async def setup(bot) -> None:
    await bot.add_cog(Lyrics(bot))
