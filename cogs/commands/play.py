import asyncio
import os
import discord
import voltricx
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv
from voltricx.exceptions import ChannelTimeoutException

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.unified_cache_manager import unified_cache
from utils.helper_function.spotify_scraper import scrape_spotify_playlist
from utils.embed_designs import play as play_design
from utils.helper_function.ratelimit import LAVALINK_SEARCH_SEM
from utils.helper_function.queue_placement import QueuePlacementView
from utils.logger.mewzik_logger import bot_logger
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()
BOT_NAME = os.getenv("BOT_NAME")


class Play(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_voice(self, ctx):
        try:
            user = ctx.author
            if not user.voice or not user.voice.channel:
                if bot_logger.enabled:
                    await bot_logger.async_incoming(
                        "Voice check failed — user not in voice channel",
                        user_id=user.id,
                        user=str(user),
                        guild_id=ctx.guild.id,
                    )
                schedule_delete(await ctx.send(view=play_design.not_in_voice()))
                return False

            voice_client = ctx.guild.voice_client

            if not voice_client:
                channel = user.voice.channel
                try:
                    try:
                        await voltricx.Pool.wait_until_ready()
                    except AttributeError:
                        pass

                    if bot_logger.enabled:
                        await bot_logger.async_outgoing(
                            "Voice channel connection request",
                            channel=channel.name,
                            channel_id=channel.id,
                            guild_id=ctx.guild.id,
                            guild=ctx.guild.name,
                        )

                    with bot_logger.timer() as t:
                        player: LavaMusic = await channel.connect(cls=LavaMusic, timeout=45, reconnect=True, self_deaf=True)

                    if bot_logger.enabled:
                        await bot_logger.async_incoming(
                            "Voice channel connected",
                            channel=channel.name,
                            channel_id=channel.id,
                            guild_id=ctx.guild.id,
                            elapsed_ms=t.elapsed_ms,
                        )

                except ChannelTimeoutException as e:
                    print(f"\033[91m[ERROR] Channel Timeout Exception\033[0m: {e}")
                    if bot_logger.enabled:
                        await bot_logger.async_error(
                            "Voice channel connection timed out — retrying",
                            channel=channel.name,
                            channel_id=channel.id,
                            guild_id=ctx.guild.id,
                            error=str(e),
                        )
                    await asyncio.sleep(2)
                    try:
                        if bot_logger.enabled:
                            await bot_logger.async_outgoing(
                                "Voice channel connection retry",
                                channel=channel.name,
                                channel_id=channel.id,
                                guild_id=ctx.guild.id,
                            )
                        player: LavaMusic = await channel.connect(cls=LavaMusic, timeout=45, reconnect=True, self_deaf=True)
                        if bot_logger.enabled:
                            await bot_logger.async_incoming(
                                "Voice channel connected on retry",
                                channel=channel.name,
                                guild_id=ctx.guild.id,
                            )
                    except Exception as e:
                        print(f"\033[91m[ERROR] Voice Connection Retry Error\033[0m: {e}")
                        if bot_logger.enabled:
                            await bot_logger.async_error(
                                "Voice channel connection retry failed",
                                channel=channel.name,
                                guild_id=ctx.guild.id,
                                error=str(e),
                            )
                        schedule_delete(await ctx.send(view=play_design.connect_failed()))
                        return False
                except Exception as e:
                    print(f"\033[91m[ERROR] Voice Connection Error\033[0m: {e}")
                    if bot_logger.enabled:
                        await bot_logger.async_error(
                            "Voice channel connection failed",
                            channel=channel.name,
                            channel_id=channel.id,
                            guild_id=ctx.guild.id,
                            error=str(e),
                        )
                    schedule_delete(await ctx.send(view=play_design.connect_failed()))
                    return False

                try:
                    schedule_delete(await ctx.send(view=play_design.bot_joined(self.bot.user.name, channel.name)))
                    player.home = ctx.channel
                    return True
                except Exception as e:
                    print(f"\033[91m[ERROR] Voice Join Message Error\033[0m: {e}")
                    if bot_logger.enabled:
                        await bot_logger.async_error(
                            "Voice join message send failed",
                            channel=channel.name,
                            guild_id=ctx.guild.id,
                            error=str(e),
                        )
                    player.home = ctx.channel
                    return True

            elif voice_client.channel != user.voice.channel:
                if bot_logger.enabled:
                    await bot_logger.async_incoming(
                        "Voice check failed — user in different channel",
                        user_id=user.id,
                        user_channel=user.voice.channel.name,
                        bot_channel=voice_client.channel.name,
                        guild_id=ctx.guild.id,
                    )
                schedule_delete(await ctx.send(view=play_design.different_voice()))
                return False

            return True
        except Exception as e:
            print(f"\033[91m[ERROR] Ensure Voice Error\033[0m: {e}")
            if bot_logger.enabled:
                await bot_logger.async_error(
                    "ensure_voice raised unexpected error",
                    guild_id=ctx.guild.id,
                    error=str(e),
                )
            schedule_delete(await ctx.send(view=play_design.connect_failed()))
            return False

    async def get_user_engine(self, user_id):
        return await unified_cache.get_user_engine(user_id)

    @commands.hybrid_command(name="play", description="Play a song or playlist.", aliases=["p"])
    @commands.cooldown(1, 2, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def play(self, ctx: commands.Context, *, query: str):

        # ── Incoming request log ───────────────────────────────────────────────
        if bot_logger.enabled:
            await bot_logger.async_incoming(
                "play command received",
                user_id=ctx.author.id,
                user=str(ctx.author),
                guild_id=ctx.guild.id,
                guild=ctx.guild.name,
                channel_id=ctx.channel.id,
                channel=ctx.channel.name,
                invocation=ctx.invoked_with,
                query=query,
            )

        try:
            if not await enforce_setup(ctx):
                if bot_logger.enabled:
                    await bot_logger.async_incoming(
                        "play aborted — server setup not complete",
                        guild_id=ctx.guild.id,
                    )
                return
            if not await self.ensure_voice(ctx):
                return

            player: LavaMusic = ctx.guild.voice_client

            if not isinstance(player.queue, voltricx.Queue):
                player.queue = voltricx.Queue()

            player.home = ctx.channel

            # ── Direct URL detection ───────────────────────────────────────────
            # When the query is a direct link, let Lavalink resolve it natively
            # so playlists/albums return all their tracks instead of one result.
            is_direct_url = query.startswith("http://") or query.startswith("https://")

            # Map known domains to a friendly source label for logging
            _URL_PLATFORM_MAP = {
                "open.spotify.com": "spotify",
                "spotify.com": "spotify",
                "youtube.com": "youtube",
                "youtu.be": "youtube",
                "music.youtube.com": "youtube_music",
                "soundcloud.com": "soundcloud",
                "music.apple.com": "apple_music",
                "deezer.com": "deezer",
                "deezer.page.link": "deezer",
                "saavn.com": "jiosaavn",
                "jiosaavn.com": "jiosaavn",
                "bandcamp.com": "bandcamp",
                "twitch.tv": "twitch",
            }

            detected_platform = None
            if is_direct_url:
                query_lower = query.lower()
                for domain, platform in _URL_PLATFORM_MAP.items():
                    if domain in query_lower:
                        detected_platform = platform
                        break

                # Strip tracking/sharing query params (?si=, ?utm_source=, etc.)
                # that can cause LavaSrc to fail resolving Spotify/Deezer URLs.
                # Only strip for platforms where the resource ID lives in the URL
                # path — NOT for YouTube/Twitch where ?v= / ?list= ARE the ID.
                _STRIP_QUERY_PLATFORMS = {"spotify", "deezer", "apple_music", "jiosaavn", "bandcamp"}
                if "?" in query and detected_platform in _STRIP_QUERY_PLATFORMS:
                    query = query.split("?")[0]

                if bot_logger.enabled:
                    bot_logger.debug(
                        "Direct URL detected — bypassing search engine loop",
                        query=query,
                        detected_platform=detected_platform or "unknown",
                        user_id=ctx.author.id,
                        guild_id=ctx.guild.id,
                    )

            tracks = None

            # Resolve which Lavalink node will handle this guild's requests
            _node = None
            try:
                _node = voltricx.Pool.get_node()
            except Exception:
                all_nodes = list(voltricx.Pool.nodes().values())
                _node = all_nodes[0] if all_nodes else None

            _node_id  = getattr(_node, "identifier", "unknown") if _node else "unknown"
            _node_uri = getattr(_node, "uri", "unknown")         if _node else "unknown"
            _node_region = getattr(_node, "config", "global")    if _node else "global"

            if is_direct_url:
                # ── Direct URL path: pass raw URL to Lavalink without source prefix ──
                try:
                    if bot_logger.enabled:
                        await bot_logger.async_outgoing(
                            "Lavalink direct URL load request",
                            query=query,
                            platform=detected_platform or "unknown",
                            guild_id=ctx.guild.id,
                            node_id=_node_id,
                            node_uri=_node_uri,
                        )

                    with bot_logger.timer() as t:
                        tracks = await voltricx.Playable.search(query)

                    if tracks:
                        player.source = detected_platform or "direct_url"
                        if bot_logger.enabled:
                            await bot_logger.async_incoming(
                                "Lavalink direct URL load — tracks found",
                                platform=detected_platform or "unknown",
                                is_playlist=isinstance(tracks, voltricx.Playlist),
                                tracks_found=len(getattr(tracks, "tracks", tracks)) if tracks else 0,
                                elapsed_ms=t.elapsed_ms,
                                node_id=_node_id,
                                guild_id=ctx.guild.id,
                            )
                except voltricx.LavalinkLoadException as e:
                    # Expected for Spotify playlists/albums — LavaSrc can't resolve
                    # them natively; the embed-API fallback below will handle it.
                    print(f"\033[93m[WARN] Lavalink direct URL load failed (fallback will retry)\033[0m: {e}")
                    if bot_logger.enabled:
                        bot_logger.debug(
                            "Lavalink direct URL load failed — will attempt fallback",
                            query=query,
                            platform=detected_platform or "unknown",
                            node_id=_node_id,
                            guild_id=ctx.guild.id,
                            error=str(e),
                        )
                except Exception as e:
                    print(f"\033[91m[ERROR] Direct URL Search Error\033[0m: {e}")
                    if bot_logger.enabled:
                        await bot_logger.async_error(
                            "Lavalink direct URL search error",
                            query=query,
                            platform=detected_platform or "unknown",
                            node_id=_node_id,
                            guild_id=ctx.guild.id,
                            error=str(e),
                        )

                # ── Fallback: if direct URL load returned nothing ─────────────
                if not tracks:
                    # For Spotify playlists/albums: fetch track list from Spotify's
                    # embed page (free, no API key) and search each track individually.
                    if detected_platform == "spotify" and any(seg in query for seg in ("/playlist/", "/album/")):
                        try:
                            from collections import deque

                            wait_msg = await ctx.send(view=play_design.loading_playlist(None))

                            sp_result = await scrape_spotify_playlist(query)

                            if sp_result and sp_result.tracks:
                                if bot_logger.enabled:
                                    bot_logger.debug(
                                        "Spotify scraper — fetched track names",
                                        sp_type=sp_result.sp_type,
                                        track_count=len(sp_result.tracks),
                                        guild_id=ctx.guild.id,
                                    )

                                user_engine = await self.get_user_engine(ctx.author.id)
                                if user_engine is None or not await unified_cache.is_engine_enabled(user_engine):
                                    user_engine = "ytsearch"
                                    if not await unified_cache.is_engine_enabled("ytsearch"):
                                        user_engine = "dzsearch"

                                name_queue = deque(sp_result.tracks)
                                total_tracks = len(sp_result.tracks)

                                try:
                                    await wait_msg.delete()
                                except Exception:
                                    pass

                                schedule_delete(await ctx.send(view=play_design.loading_spotify(sp_result.pl_name, sp_result.sp_type, total_tracks)))

                                # ── Find first playable track and start playback immediately ──
                                first_found = False
                                while name_queue and not first_found:
                                    track_name = name_queue.popleft()
                                    try:
                                        async with LAVALINK_SEARCH_SEM:
                                            result = await voltricx.Playable.search(track_name, source="spsearch")
                                            if not result:
                                                result = await voltricx.Playable.search(track_name, source=user_engine)
                                        if result:
                                            t = (
                                                result[0]
                                                if not isinstance(result, voltricx.Playlist)
                                                else (result.tracks[0] if result.tracks else None)
                                            )
                                            if t:
                                                player.metadata[t] = {"requestor": ctx.author, "source": "spotify"}
                                                if not player.playing:
                                                    try:
                                                        await player.play(t, replace=True)
                                                    except Exception as e:
                                                        print(f"\033[91m[ERROR] Player Play Error\033[0m: {e}")
                                                else:
                                                    player.queue.put(t)
                                                first_found = True
                                    except Exception:
                                        pass

                                if first_found:
                                    # ── Queue the rest in the background (0.75 s per track) ──
                                    async def _bg_fill():
                                        while name_queue:
                                            if not player.check_queue_size():
                                                break
                                            _track_name = name_queue.popleft()
                                            try:
                                                async with LAVALINK_SEARCH_SEM:
                                                    _result = await voltricx.Playable.search(_track_name, source="spsearch")
                                                    if not _result:
                                                        _result = await voltricx.Playable.search(_track_name, source=user_engine)
                                                if _result:
                                                    _t = (
                                                        _result[0]
                                                        if not isinstance(_result, voltricx.Playlist)
                                                        else (_result.tracks[0] if _result.tracks else None)
                                                    )
                                                    if _t:
                                                        player.metadata[_t] = {"requestor": ctx.author, "source": "spotify"}
                                                        player.queue.put(_t)
                                            except Exception:
                                                pass
                                            await asyncio.sleep(0.75)

                                    asyncio.create_task(_bg_fill())

                                    if player.paused:
                                        await player.pause(False)

                                    if bot_logger.enabled:
                                        bot_logger.debug(
                                            "Spotify playlist — first track playing, rest queuing in background",
                                            total_tracks=total_tracks,
                                            guild_id=ctx.guild.id,
                                        )
                                return
                        except Exception as sp_err:
                            print(f"\033[91m[ERROR] Spotify playlist scraper error\033[0m: {sp_err}")
                            if bot_logger.enabled:
                                await bot_logger.async_error(
                                    "Spotify playlist scraper failed",
                                    error=str(sp_err),
                                    guild_id=ctx.guild.id,
                                )

                    # ── Generic single-track fallback for other platforms ──────
                    fallback_query = None

                    # For Spotify/Deezer single tracks: use oEmbed for the title
                    if detected_platform in ("spotify", "deezer", "apple_music"):
                        try:
                            import aiohttp
                            oembed_url = f"https://open.spotify.com/oembed?url={query}"
                            async with aiohttp.ClientSession() as session:
                                async with session.get(oembed_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                                    if resp.status == 200:
                                        data = await resp.json()
                                        title = data.get("title", "")
                                        if title:
                                            fallback_query = title
                                            if bot_logger.enabled:
                                                bot_logger.debug(
                                                    "oEmbed fallback — got title",
                                                    title=title,
                                                    guild_id=ctx.guild.id,
                                                )
                        except Exception as oe:
                            if bot_logger.enabled:
                                bot_logger.debug(
                                    "oEmbed fallback failed",
                                    error=str(oe),
                                    guild_id=ctx.guild.id,
                                )

                    # Generic fallback: try to extract a readable name from URL path
                    # but skip generic segments like "playlist", "track", "album", etc.
                    if not fallback_query:
                        _GENERIC_SEGMENTS = {
                            "playlist", "track", "album", "artist", "episode",
                            "show", "song", "set", "sets", "embed", "intl-en",
                        }
                        try:
                            from urllib.parse import urlparse
                            path_segments = [
                                s for s in urlparse(query).path.split("/")
                                if s and s.lower() not in _GENERIC_SEGMENTS
                            ]
                            # Use last segment that looks like a readable slug
                            import re
                            for seg in reversed(path_segments):
                                candidate = seg.replace("-", " ").replace("_", " ")
                                has_words = any(c.isalpha() for c in candidate)
                                is_not_id = not all(c in "0123456789abcdefABCDEF" for c in seg.replace("-", ""))
                                # Also reject Spotify/Deezer base62 IDs (20-24 alphanumeric chars)
                                is_base62_id = bool(re.fullmatch(r"[A-Za-z0-9]{15,30}", seg))
                                if has_words and is_not_id and not is_base62_id and len(candidate) > 3:
                                    fallback_query = candidate
                                    break
                        except Exception:
                            pass

                    if fallback_query:
                        if bot_logger.enabled:
                            bot_logger.debug(
                                "Direct URL failed — falling back to text search",
                                original_query=query,
                                fallback_query=fallback_query,
                                guild_id=ctx.guild.id,
                            )
                        query = fallback_query
                        is_direct_url = False  # let it fall through to the text search below

            if not is_direct_url and not tracks:
                # ── Text query path: use tiered search engine loop ───────────────
                user_engine = await self.get_user_engine(ctx.author.id)

                if bot_logger.enabled:
                    bot_logger.debug(
                        "User engine preference loaded",
                        user_id=ctx.author.id,
                        engine=user_engine,
                    )

                if user_engine is None or not await unified_cache.is_engine_enabled(user_engine):
                    fallback = "ytsearch"
                    if not await unified_cache.is_engine_enabled("ytsearch"):
                        fallback = "dzsearch"

                    if bot_logger.enabled:
                        bot_logger.debug(
                            "User engine unavailable — applying fallback",
                            user_id=ctx.author.id,
                            preferred_engine=user_engine,
                            fallback_engine=fallback,
                        )
                    user_engine = fallback

                # Preference order: User engine > YouTube > Deezer > YouTube Music > Spotify > JioSaavn > SoundCloud > Apple Music > yt-dlp
                search_sources = [f"{user_engine}", "ytsearch", "dzsearch", "ytmsearch", "spsearch", "jssearch", "scsearch", "amsearch", "ytdl"]

                # Resolve unique sources, keeping order (stable)
                seen = set()
                unique_sources = []
                for s in search_sources:
                    if s not in seen:
                        unique_sources.append(s)
                        seen.add(s)
                search_sources = unique_sources

                if bot_logger.enabled:
                    bot_logger.debug(
                        "Search sources sequence updated",
                        user_id=ctx.author.id,
                        seq=search_sources,
                    )

                for source in search_sources:
                    try:
                        if bot_logger.enabled:
                            await bot_logger.async_outgoing(
                                "Lavalink search request",
                                source=source,
                                query=query,
                                guild_id=ctx.guild.id,
                                node_id=_node_id,
                                node_uri=_node_uri,
                                node_region=_node_region,
                            )

                        with bot_logger.timer() as t:
                            tracks = await voltricx.Playable.search(query, source=source)

                        if tracks:
                            player.source = source
                            if bot_logger.enabled:
                                await bot_logger.async_incoming(
                                    "Lavalink search response — tracks found",
                                    source=source,
                                    tracks_found=len(tracks) if hasattr(tracks, "__len__") else 1,
                                    elapsed_ms=t.elapsed_ms,
                                    node_id=_node_id,
                                    node_uri=_node_uri,
                                    guild_id=ctx.guild.id,
                                )
                            break
                        else:
                            if bot_logger.enabled:
                                await bot_logger.async_incoming(
                                    "Lavalink search response — no results for source",
                                    source=source,
                                    elapsed_ms=t.elapsed_ms,
                                    node_id=_node_id,
                                    guild_id=ctx.guild.id,
                                )
                    except voltricx.LavalinkLoadException as e:
                        print(f"\033[91m[ERROR] Lavalink Load Exception\033[0m: {e}")
                        if bot_logger.enabled:
                            await bot_logger.async_error(
                                "Lavalink load exception",
                                source=source,
                                query=query,
                                node_id=_node_id,
                                node_uri=_node_uri,
                                guild_id=ctx.guild.id,
                                error=str(e),
                            )
                        continue
                    except Exception as e:
                        print(f"\033[91m[ERROR] Search Error\033[0m: {e}")
                        if bot_logger.enabled:
                            await bot_logger.async_error(
                                "Lavalink search error",
                                source=source,
                                query=query,
                                node_id=_node_id,
                                guild_id=ctx.guild.id,
                                error=str(e),
                            )
                        continue

            if not tracks:
                if bot_logger.enabled:
                    await bot_logger.async_incoming(
                        "play command — no tracks found across all sources",
                        query=query,
                        user_id=ctx.author.id,
                        guild_id=ctx.guild.id,
                    )
                return schedule_delete(await ctx.send(view=play_design.no_results(ctx.author.mention)))
        except Exception as e:
            print(f"\033[91m[ERROR] Play Command Error\033[0m: {e}")
            if bot_logger.enabled:
                await bot_logger.async_error(
                    "play command raised unexpected error during search phase",
                    user_id=ctx.author.id,
                    guild_id=ctx.guild.id,
                    query=query,
                    error=str(e),
                )
            schedule_delete(await ctx.send(view=play_design.play_error()))
            return

        try:
            if isinstance(tracks, voltricx.Playlist):
                
                t_list = getattr(tracks, "tracks", [])
                tracks_to_add = t_list[:100] if len(t_list) > 100 else t_list

                wait_msg = await ctx.send(view=play_design.loading_playlist(None))

                if bot_logger.enabled:
                    await bot_logger.async_incoming(
                        "Playlist queued",
                        playlist=getattr(tracks, "name", "Unknown Playlist"),
                        track_count=len(tracks_to_add),
                        user_id=ctx.author.id,
                        guild_id=ctx.guild.id,
                    )

                for track in tracks_to_add:
                    if not player.check_queue_size():
                        if bot_logger.enabled:
                            await bot_logger.async_incoming(
                                "Queue full — playlist partially added",
                                guild_id=ctx.guild.id,
                                user_id=ctx.author.id,
                            )
                        return schedule_delete(await ctx.send(view=play_design.queue_full(ctx.author.mention)))

                    player.metadata[track] = {"requestor": ctx.author, "source": detected_platform or track.source}
                    player.queue.put(track)
                    if player.paused:
                        await player.pause(False)

                added = len(tracks_to_add)
                # Bot activity is no longer tracked separately
                pass

                try:
                    await wait_msg.delete()
                except Exception:
                    pass

                schedule_delete(await ctx.send(view=play_design.playlist_added(getattr(tracks, 'name', 'Unknown Playlist'), added)))
            else:
                track: voltricx.Playable = tracks[0]

                if not player.check_queue_size():
                    if bot_logger.enabled:
                        await bot_logger.async_incoming(
                            "Queue full — track not added",
                            guild_id=ctx.guild.id,
                            user_id=ctx.author.id,
                            track=track.title,
                        )
                    return schedule_delete(await ctx.send(view=play_design.queue_full(ctx.author.mention)))

                duration_ms = track.length
                minutes, seconds = divmod(duration_ms // 1000, 60)
                formatted_duration = f"{minutes:02}m {seconds:02}s"
                track_source = detected_platform or track.source

                # ── Something already playing → ask where to place the track ──
                if player.playing:
                    if bot_logger.enabled:
                        await bot_logger.async_incoming(
                            "Track add — prompting queue placement",
                            track=track.title,
                            artist=track.author,
                            user_id=ctx.author.id,
                            guild_id=ctx.guild.id,
                        )
                    placement_view = QueuePlacementView(
                        player=player,
                        track=track,
                        requestor=ctx.author,
                        duration=formatted_duration,
                        source=track_source,
                    )
                    placement_view.message = await ctx.send(view=placement_view)
                    return

                # ── Nothing playing → queue and start immediately ──
                player.metadata[track] = {"requestor": ctx.author, "source": track_source}
                player.queue.put(track)
                if player.paused:
                    await player.pause(False)

                if bot_logger.enabled:
                    await bot_logger.async_incoming(
                        "Track queued",
                        track=track.title,
                        artist=track.author,
                        source=track.source,
                        duration=formatted_duration,
                        user_id=ctx.author.id,
                        guild_id=ctx.guild.id,
                    )

                schedule_delete(await ctx.send(view=play_design.track_added(
                    track.title,
                    track.author,
                    formatted_duration,
                    getattr(track, "artwork", None),
                    f"Requested by {ctx.author.display_name}",
                )))

            if not player.playing:
                try:
                    next_track = player.queue.get()

                    # Resolve the node the player is connected to
                    _pnode = getattr(player, "node", None)
                    _pnode_id  = getattr(_pnode, "identifier", "unknown") if _pnode else "unknown"
                    _pnode_uri = getattr(_pnode, "uri", "unknown")         if _pnode else "unknown"
                    _pnode_region = getattr(_pnode, "region", "global")    if _pnode else "global"

                    if bot_logger.enabled:
                        await bot_logger.async_outgoing(
                            "Sending play request to Lavalink node",
                            track_title=next_track.title,
                            track_id=getattr(next_track, "identifier", "unknown"),
                            source=getattr(next_track, "source", "unknown"),
                            node_id=_pnode_id,
                            node_uri=_pnode_uri,
                            node_region=_pnode_region,
                            guild_id=ctx.guild.id,
                        )

                    with bot_logger.timer() as pt:
                        await player.play(next_track, replace=True)

                    if bot_logger.enabled:
                        await bot_logger.async_incoming(
                            "Lavalink playback started",
                            track=next_track.title,
                            source=getattr(next_track, "source", "unknown"),
                            node_id=_pnode_id,
                            node_uri=_pnode_uri,
                            elapsed_ms=pt.elapsed_ms,
                            guild_id=ctx.guild.id,
                        )
                except Exception as e:
                    print(f"\033[91m[ERROR] Player Play Error\033[0m: {e}")
                    if bot_logger.enabled:
                        await bot_logger.async_error(
                            "Lavalink play request failed",
                            guild_id=ctx.guild.id,
                            error=str(e),
                        )
        except Exception as e:
            print(f"\033[91m[ERROR] Track Processing Error\033[0m: {e}")
            if bot_logger.enabled:
                await bot_logger.async_error(
                    "play command raised unexpected error during track processing",
                    user_id=ctx.author.id,
                    guild_id=ctx.guild.id,
                    error=str(e),
                )
            schedule_delete(await ctx.send(view=play_design.track_error()))


async def setup(bot):
    await bot.add_cog(Play(bot))
