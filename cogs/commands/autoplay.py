"""
Autoplay command — shows bot-curated playlists in an ephemeral panel.
Users pick a playlist from a dropdown (or play all). Tracks are served
from the pre-fetched AutoplayCacheManager so Lavalink isn't hammered
on every play request.
"""
from __future__ import annotations

import asyncio
import discord
from discord.ext import commands
from discord.ext.commands import BucketType

import voltricx

import os
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.autoplay_cache import autoplay_cache
from utils.helper_function.setup_enforcer import enforce_setup
from utils.embed_designs import autoplay as autoplay_design
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.ratelimit import LAVALINK_SEARCH_SEM
from utils.helper_function.unified_cache_manager import unified_cache
from utils.logger.mewzik_logger import bot_logger
from utils.helper_function.bot_config import EMBED_COLOR

load_dotenv()


_AUTOPLAY_TARGET = 5   # keep this many tracks in the queue at all times

# ── Helper: resolve and queue a single cached track dict ─────────────────────

async def _resolve_track(td: dict, player: LavaMusic, requestor: discord.Member) -> bool:
    """Resolve one cached track dict and push it onto the player queue. Returns True if queued."""
    uri = td.get("uri")
    query = td.get("query")
    # YouTube tracks are cached with query=None — build from title+author instead
    if not query:
        title = td.get("title", "")
        author = td.get("author", "")
        query = f"{title} {author}".strip() or None
    t = None

    # Resolve user's preferred engine for fresh searches
    user_engine = await unified_cache.get_user_engine(requestor.id)
    if user_engine is None or not await unified_cache.is_engine_enabled(user_engine):
        user_engine = "ytsearch"
        if not await unified_cache.is_engine_enabled("ytsearch"):
            user_engine = "dzsearch"

    # Re-fetch a fresh URL using the track title — cached YouTube IDs expire.
    if query:
        search_sources = [user_engine, "ytsearch", "dzsearch", "ytmsearch", "spsearch", "jssearch", "scsearch", "amsearch", "ytdl"]
        seen = set()
        unique_sources = [s for s in search_sources if not (s in seen or seen.add(s))]
        for source in unique_sources:
            try:
                async with LAVALINK_SEARCH_SEM:
                    results = await voltricx.Playable.search(query, source=source)
                if results:
                    t = results.tracks[0] if isinstance(results, voltricx.Playlist) else results[0]
                    break
            except Exception:
                continue

    # Last resort: direct URI (only for non-YouTube sources that don't expire)
    if not t and uri and "youtube" not in uri:
        try:
            async with LAVALINK_SEARCH_SEM:
                results = await voltricx.Playable.search(uri)
            if results:
                t = results.tracks[0] if isinstance(results, voltricx.Playlist) else results[0]
        except Exception:
            pass

    if t:
        player.metadata[t] = {"requestor": requestor, "source": td.get("source", "autoplay")}
        player.queue.put(t)
        return True
    return False


# ── Helper: queue an initial batch and register the session ───────────────────

async def _queue_cached_tracks(
    tracks: list,
    player: LavaMusic,
    requestor: discord.Member,
    guild_id: int,
) -> int:
    """
    Queue the first _AUTOPLAY_TARGET tracks immediately and register the remaining
    tracks as an autoplay session so the queue stays topped up on every track end.
    Returns number queued in this call.
    """
    batch = tracks[:_AUTOPLAY_TARGET]
    remaining = tracks[_AUTOPLAY_TARGET:]
    added = 0
    was_playing = player.playing  # snapshot BEFORE we touch anything

    # ── Step 1: resolve and play the FIRST track immediately ─────────────────
    first_queued = False
    batch_iter = iter(batch)
    for td in batch_iter:
        if not player.check_queue_size():
            break
        try:
            queued = await _resolve_track(td, player, requestor)
            if queued:
                added += 1
                first_queued = True
                break
        except Exception:
            continue

    # Start playback right away if nothing was already playing
    if first_queued and not was_playing:
        try:
            next_track = player.queue.get()
            await player.play(next_track, replace=False)
        except Exception as e:
            print(f"\033[91m[ERROR] Autoplay - start playback error\033[0m: {e}")

    if player.paused and first_queued:
        await player.pause(False)

    # ── Step 2: resolve and queue the rest of the batch in the background ─────
    remaining_batch = list(batch_iter)  # whatever batch tracks weren't consumed above

    async def _bg_fill_batch():
        nonlocal added
        for td in remaining_batch:
            if not player.check_queue_size():
                break
            try:
                queued = await _resolve_track(td, player, requestor)
                if queued:
                    added += 1
            except Exception:
                pass
            await asyncio.sleep(0.75)

    if remaining_batch:
        asyncio.create_task(_bg_fill_batch())

    # ── Step 3: register the session for smart top-up ─────────────────────────
    # Store ALL tracks so the playlist loops back to the start once exhausted.
    # Position starts after the initial batch so we don't re-queue those tracks.
    autoplay_cache.start_session(guild_id, tracks, min(_AUTOPLAY_TARGET, len(tracks)), requestor)

    return added


# ── Select: playlist dropdown ─────────────────────────────────────────────────

class AutoplaySelect(discord.ui.Select):
    def __init__(self, playlists: list, parent_view: "AutoPlayView"):
        self._view_ref = parent_view
        options = [
            discord.SelectOption(
                label=pl["name"][:100],
                value=pl["id"],
                description=f"{pl['platform']} · {pl['track_count']} tracks",
            )
            for pl in playlists[:25]
        ]
        super().__init__(
            placeholder="Choose a playlist to play…",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        await self._view_ref.play_selection(interaction, playlist_id=self.values[0])


# ── Button: Play All ──────────────────────────────────────────────────────────

class PlayAllButton(discord.ui.Button):
    def __init__(self, parent_view: "AutoPlayView"):
        super().__init__(label="Play All 🎶", style=discord.ButtonStyle.green)
        self._view_ref = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self._view_ref.play_selection(interaction, playlist_id=None)


# ── Main ephemeral view ───────────────────────────────────────────────────────

class AutoPlayView(discord.ui.LayoutView):
    def __init__(self, ctx: commands.Context, playlists: list):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.playlists = playlists

        self.add_item(autoplay_design.autoplay_picker_container(playlists))

        # Select dropdown row
        select_row = discord.ui.ActionRow()
        select_row.add_item(AutoplaySelect(playlists, self))
        self.add_item(select_row)

        # Play All button row
        button_row = discord.ui.ActionRow()
        button_row.add_item(PlayAllButton(self))
        self.add_item(button_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Only the command invoker can use this.", ephemeral=True
            )
            return False
        return True

    async def play_selection(
        self,
        interaction: discord.Interaction,
        playlist_id: "str | None",
    ):
        """Join voice and queue the chosen playlist (or all playlists when None)."""
        await interaction.response.defer(ephemeral=True)

        ctx = self.ctx

        # Voice join — delegate to Play cog if available
        play_cog = ctx.bot.cogs.get("Play")
        if play_cog:
            if not await play_cog.ensure_voice(ctx):
                return
        else:
            if not ctx.author.voice or not ctx.author.voice.channel:
                await interaction.followup.send(
                    "You need to be in a voice channel.", ephemeral=True
                )
                return
            vc = ctx.guild.voice_client
            if not vc:
                try:
                    await ctx.author.voice.channel.connect(
                        cls=LavaMusic, timeout=45, reconnect=True, self_deaf=True
                    )
                except Exception:
                    await interaction.followup.send(
                        "Failed to join your voice channel.", ephemeral=True
                    )
                    return
            elif vc.channel != ctx.author.voice.channel:
                await interaction.followup.send(
                    "You must be in the same voice channel as me.", ephemeral=True
                )
                return

        player: LavaMusic = ctx.guild.voice_client
        if not isinstance(player, LavaMusic):
            await interaction.followup.send(
                "No active player found. Please try again.", ephemeral=True
            )
            return

        player.home = ctx.channel

        # Gather tracks
        if playlist_id:
            pl = autoplay_cache.get_playlist_by_id(playlist_id)
            if not pl:
                await interaction.followup.send("Playlist not found.", ephemeral=True)
                return
            tracks = autoplay_cache.get_tracks(playlist_id)
            label = pl["name"]
        else:
            tracks = autoplay_cache.get_all_tracks()
            label = "All Playlists"

        if not tracks:
            await interaction.followup.send(
                f"No cached tracks for **{label}**. An admin may need to re-add the playlist.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"⏳ Queuing **{label}** — starting with {_AUTOPLAY_TARGET} tracks, rest will follow automatically…",
            ephemeral=True,
        )

        # Stop any existing autoplay session, and any playlist session (mutually
        # exclusive — only one thing should be trickling tracks into this guild's
        # queue at a time), before starting a new one.
        autoplay_cache.stop_session(ctx.guild.id)
        from cogs.commands.playlist import stop_playlist_session
        stop_playlist_session(ctx.guild.id)

        added = await _queue_cached_tracks(tracks, player, ctx.author, ctx.guild.id)

        if bot_logger.enabled:
            await bot_logger.async_incoming(
                "autoplay — playlist queued",
                label=label,
                playlist_id=playlist_id,
                tracks_queued=added,
                guild_id=ctx.guild.id,
                user_id=ctx.author.id,
            )

        self.stop()


# ── Cog ───────────────────────────────────────────────────────────────────────

class AutoPlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="autoplay",
        description="Pick a curated playlist to play automatically. Run again to stop autoplay.",
        aliases=["auto", "ap"],
    )
    @commands.cooldown(1, 5, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def autoplay(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return

        # ── Toggle OFF if a session is already running for this guild ─────────
        if autoplay_cache.has_session(ctx.guild.id):
            autoplay_cache.stop_session(ctx.guild.id)
            await ctx.send(view=autoplay_design.autoplay_stopped(), ephemeral=True)
            if bot_logger.enabled:
                await bot_logger.async_incoming(
                    "autoplay cmd — session stopped by user",
                    guild_id=ctx.guild.id,
                    user_id=ctx.author.id,
                )
            return

        # ── No active session — show playlist picker ───────────────────────────
        playlists = autoplay_cache.get_playlists()

        if not playlists:
            await ctx.send(view=autoplay_design.autoplay_no_playlists(), ephemeral=True)
            return

        view = AutoPlayView(ctx, playlists)
        await ctx.send(view=view, ephemeral=True)

        if bot_logger.enabled:
            await bot_logger.async_incoming(
                "autoplay cmd — panel opened",
                guild_id=ctx.guild.id,
                user_id=ctx.author.id,
                playlist_count=len(playlists),
            )


async def setup(bot):
    await bot.add_cog(AutoPlay(bot))
