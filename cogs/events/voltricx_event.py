import asyncio
from typing import Any
import discord
from discord.ext import commands
import voltricx
from voltricx.player import Player
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.leaderboard_counter import increment_user_count, increment_user_source
from utils.helper_function.autoplay_cache import autoplay_cache
from utils.helper_function.unified_cache_manager import unified_cache
from utils.embed_designs import session as session_design
from utils.embed_designs import voltricx_events as vx_design
from .player import PlayerCard


class Voltricx_Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.player_messages = {}


    # Platform icons via Google favicon service — stable URLs that never expire,
    # unlike Discord attachment links (which carry an `ex=` expiry timestamp).
    _FAVICON = "https://www.google.com/s2/favicons?domain={}&sz=128"

    platform_data = {
            "spsearch": ("Spotify", _FAVICON.format("spotify.com")),
            "jssearch": ("JioSaavn", _FAVICON.format("jiosaavn.com")),
            "scsearch": ("SoundCloud", _FAVICON.format("soundcloud.com")),
            "ytmsearch": ("YouTube Music", _FAVICON.format("music.youtube.com")),
            "ytsearch": ("YouTube", _FAVICON.format("youtube.com")),
            "spotify": ("Spotify", _FAVICON.format("spotify.com")),
            "dzsearch": ("Deezer", _FAVICON.format("deezer.com")),
            "deezer": ("Deezer", _FAVICON.format("deezer.com")),
            "jiosaavn": ("JioSaavn", _FAVICON.format("jiosaavn.com")),
            "amsearch": ("Apple Music", _FAVICON.format("music.apple.com")),
            "ytdl": ("yt-dlp", _FAVICON.format("youtube.com")),
            "youtube": ("YouTube", _FAVICON.format("youtube.com")),
            "soundcloud": ("SoundCloud", _FAVICON.format("soundcloud.com")),
            "apple_music": ("Apple Music", _FAVICON.format("music.apple.com")),
        }
                        
   
    @commands.Cog.listener()
    async def on_voltricx_track_start(self, player: LavaMusic, track: voltricx.Playable):
        if player is None:
            return

        metadata = player.metadata.get(track, {})
        requestor = metadata.get("requestor", player.client.user)

        duration_ms = track.length
        minutes, seconds = divmod(duration_ms // 1000, 60)
        formatted_duration = f"{minutes:02}m {seconds:02}s"

        source = metadata.get("source")
        if not source or source == "autoplay":
            source = track.source
        
        # Map raw source names to engine keys for icons
        source_map = {
            "youtube": "ytsearch",
            "spotify": "spsearch",
            "deezer": "dzsearch",
            "applemusic": "amsearch",
        }
        source = source_map.get(source, source or "unknown")

        platform, icon_url = self.platform_data.get(source, ("Unknown", " "))

        # Track play count, listening minutes, and source per user
        if requestor and not getattr(requestor, 'bot', True):
            try:
                await increment_user_count(player.guild.id, requestor.id, count=1)
            except Exception:
                pass
            try:
                await increment_user_source(requestor.id, platform)
            except Exception:
                pass
        
        if player in self.player_messages:
            previous_message_id = self.player_messages[player]
            try:
                previous_message = await player.home.fetch_message(previous_message_id)
                
                await previous_message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                print(f"Permission error: Bot can't delete the previous message in {player.home.name}")
            except Exception as e:
                await self.handle_voltricx_exception(e, "Track Start - Message Deletion")


        if not hasattr(player, 'home') or player.home is None:
            return

        # Permission check before sending embed
        perms = player.home.permissions_for(player.guild.me)
        missing = []
        if not perms.send_messages:
            missing.append("Send Messages")
        if not perms.embed_links:
            missing.append("Embed Links")
        if not perms.view_channel:
            missing.append("View Channel")

        if missing:
            if hasattr(requestor, 'send'):
                try:
                    await requestor.send(f"Missing permission(s) in #{player.home.name}: {', '.join(missing)}. Please grant the bot these permissions.")
                except Exception:
                    pass
            return

        try:
            embed_helper = PlayerCard(self.bot)
            await embed_helper.send_track_embed(player, track, formatted_duration, requestor, platform, icon_url)
            if hasattr(player, 'msg') and player.msg:
                self.player_messages[player] = player.msg.id
        except Exception as e:
            await self.handle_voltricx_exception(e, "Track Start - Embed Sending")
            try:
                await player.home.send(f"Error sending track info: {e}")
            except discord.Forbidden:
                if hasattr(requestor, 'send'):
                    await requestor.send(f"Missing permission: Send Messages in #{player.home.name}. Please grant the bot this permission.")
            
        try:
            voice_channel = player.channel
            await voice_channel.edit(status=f"♪ **{track.title}** - {track.author}")
        except discord.DiscordException as e:
            await self.handle_voltricx_exception(e, "Track Start - Channel Status Update")
        
        print(f"\033[92m[INFO] Track Started\033[0m: {track.title} in {player.guild.name} (Source: {track.source})")

    @commands.Cog.listener()
    async def on_voltricx_track_end(self, player: LavaMusic, track: voltricx.Playable, reason: str):
        if player is None or player.queue is None or player.home is None:
            return

        # Normalise reason to a plain uppercase string regardless of whether
        # voltricx passes a string or an enum object.
        reason_str = str(reason).upper().strip()

        print(f"\033[94m[INFO] Track Ended\033[0m: {track.title} in {player.guild.name} (Reason: {reason_str})")

        # Give voltricx a moment to queue the next track (autoplay / loop).
        await asyncio.sleep(0.5)

        # ── Autoplay smart-queue top-up ───────────────────────────────────────
        # Use has_session() as the sole gate — stop_callback() already calls
        # stop_session() before player.stop(), so when reason is STOPPED the
        # session is gone and this block is skipped automatically.
        guild_id = player.guild.id
        topup_scheduled = False
        if autoplay_cache.has_session(guild_id):
            session = autoplay_cache.get_session(guild_id)
            queue_size = len(player.queue)
            from cogs.commands.autoplay import _AUTOPLAY_TARGET, _resolve_track
            needed = _AUTOPLAY_TARGET - queue_size
            if needed > 0:
                batch = autoplay_cache.advance_session(guild_id, needed)
                if batch:
                    requestor = session["requestor"]
                    asyncio.create_task(self._topup_queue(player, batch, requestor))
                    topup_scheduled = True
        # ─────────────────────────────────────────────────────────────────────

        # ── Playlist smart-queue top-up (mirrors the autoplay block above) ─────
        # Each pending song carries its own requestor/engine, so this batch may
        # be a merge of multiple users' "Play All" calls — that's expected.
        from cogs.commands.playlist import (
            has_playlist_session, stop_playlist_session, advance_playlist_session, _PLAYLIST_TARGET,
        )
        if not topup_scheduled and has_playlist_session(guild_id):
            needed = _PLAYLIST_TARGET - len(player.queue)
            if needed > 0:
                batch = advance_playlist_session(guild_id, needed)
                if batch:
                    asyncio.create_task(self._topup_playlist_queue(player, batch))
                    topup_scheduled = True
        # ─────────────────────────────────────────────────────────────────────

        # Robust check: If no track started but queue is NOT empty, trigger manually.
        if player.current is None and not player.queue.is_empty:
            print(f"\033[93m[WARN] Manual Transition Triggered\033[0m: Queue not empty but current is None in {player.guild.name}.")
            try:
                next_track = player.queue.get()
                await player.play(next_track, replace=True)
                return # Next track started
            except Exception as e:
                await self.handle_voltricx_exception(e, "Track End - Manual Transition")

        if player.current is None and player.queue.is_empty:
            # A topup was just scheduled — it will restart playback once tracks resolve.
            # Don't declare session over yet; _topup_queue handles cleanup if all resolves fail.
            if topup_scheduled:
                return

            # Clear any active autoplay / playlist session — nothing left to play
            autoplay_cache.stop_session(player.guild.id)
            stop_playlist_session(player.guild.id)

            # Always reset channel status
            try:
                voice_channel = player.channel
                await voice_channel.edit(status="Ready To Play !")
            except discord.DiscordException:
                pass

            # Only clean up if inactive_player hasn't already done it (pop acts as a once-flag)
            if player in self.player_messages:
                previous_message_id = self.player_messages.pop(player)
                try:
                    previous_message = await player.home.fetch_message(previous_message_id)
                    await previous_message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    print(f"Permission error: Bot can't delete the previous message in {player.home.name}")
                except Exception as e:
                    print(f"An error occurred while deleting the previous message: {e}")
                try:
                    await player.home.send(view=session_design.session_over())
                except Exception:
                    pass

    async def is_247_enabled(self, guild_id):
        bot_id = self.bot.user.id if self.bot.user else 0
        data = await unified_cache.get_channel_set_data(guild_id, bot_id)
        return data is not None

    async def _topup_queue(self, player: LavaMusic, batch: list, requestor) -> None:
        """Resolve and add a batch of cached tracks to the player queue (background task)."""
        from cogs.commands.autoplay import _resolve_track
        for td in batch:
            try:
                await _resolve_track(td, player, requestor)
                # If player went idle while we were resolving, restart it immediately
                if not player.playing and not player.queue.is_empty and player.current is None:
                    try:
                        next_track = player.queue.get()
                        await player.play(next_track, replace=False)
                    except Exception:
                        pass
                await asyncio.sleep(0.3)
            except Exception:
                continue

        # After entire batch: if player is still idle and queue is still empty,
        # all resolves failed — trigger session-over cleanup manually
        if not player.playing and player.current is None and player.queue.is_empty:
            autoplay_cache.stop_session(player.guild.id)
            try:
                await player.channel.edit(status="Ready To Play !")
            except discord.DiscordException:
                pass
            if player in self.player_messages:
                previous_message_id = self.player_messages.pop(player)
                if getattr(player, "home", None):
                    try:
                        msg = await player.home.fetch_message(previous_message_id)
                        await msg.delete()
                    except Exception:
                        pass
                    try:
                        await player.home.send(view=session_design.session_over())
                    except Exception:
                        pass

    async def _topup_playlist_queue(self, player: LavaMusic, batch: list) -> None:
        """Resolve and add a batch of playlist songs to the queue one-by-one (background task).
        Each entry is (title, author, requestor, engine) — songs may come from different
        users' merged "Play All" sessions."""
        from cogs.commands.playlist import _resolve_one, stop_playlist_session
        for title, author, requestor, engine in batch:
            try:
                q = f"{title} {author}".strip() if author else title.strip()
                t = await _resolve_one(q, engine)
                if not t and author:
                    t = await _resolve_one(title.strip(), engine)
                if t:
                    player.metadata[t] = {"requestor": requestor, "source": t.source}
                    player.queue.put(t)
                    # If player went idle while we were resolving, restart it immediately
                    if not player.playing and not player.queue.is_empty and player.current is None:
                        try:
                            next_track = player.queue.get()
                            await player.play(next_track, replace=False)
                        except Exception:
                            pass
                await asyncio.sleep(0.3)
            except Exception:
                continue

        # After the batch: if player is still idle and queue is still empty,
        # all resolves failed — trigger session-over cleanup manually
        if not player.playing and player.current is None and player.queue.is_empty:
            stop_playlist_session(player.guild.id)
            try:
                await player.channel.edit(status="Ready To Play !")
            except discord.DiscordException:
                pass
            if player in self.player_messages:
                previous_message_id = self.player_messages.pop(player)
                if getattr(player, "home", None):
                    try:
                        msg = await player.home.fetch_message(previous_message_id)
                        await msg.delete()
                    except Exception:
                        pass
                    try:
                        await player.home.send(view=session_design.session_over())
                    except Exception:
                        pass
                
                
    @commands.Cog.listener()
    async def on_voltricx_inactive_player(self, player: Player) -> None:
        print(f"\033[93m[INFO] Inactive Player Detected\033[0m: Guild {player.guild.name} ({player.guild.id})")

        guild_id = player.guild.id
        player.filters.reset()
        player.filter_name="None"
        player.filter_status=False
        player._autoplay=voltricx.AutoPlayMode.partial

        # Clear any active autoplay session for this guild
        autoplay_cache.stop_session(guild_id)

        # Release any temp no-prefix VC ownership held by this bot for this channel.
        try:
            if player.channel:
                await unified_cache.delete_vc_assignment(guild_id, player.channel.id, self.bot.user.id)
        except Exception:
            pass

        # Always reset channel status
        try:
            voice_channel = player.channel
            await voice_channel.edit(status="Ready To Play !")
        except discord.DiscordException:
            pass

        # Delete player card and send session over (pop acts as a once-flag vs on_voltricx_track_end)
        if player in self.player_messages:
            previous_message_id = self.player_messages.pop(player)
            if hasattr(player, 'home') and player.home:
                try:
                    previous_message = await player.home.fetch_message(previous_message_id)
                    await previous_message.delete()
                except (discord.NotFound, discord.Forbidden, Exception):
                    pass
                try:
                    await player.home.send(view=session_design.session_over())
                except Exception:
                    pass

        if await self.is_247_enabled(guild_id):
            return

        timeout = getattr(player, "inactive_timeout", 300)
        view = session_design.inactive_player(timeout)

        if not hasattr(player, 'home') or player.home is None:
            return
        perms = player.home.permissions_for(player.guild.me)
        missing = []
        if not perms.send_messages:
            missing.append("Send Messages")
        if not perms.embed_links:
            missing.append("Embed Links")
        if not perms.view_channel:
            missing.append("View Channel")
        if missing:
            requestor = getattr(player, 'last_requestor', None)
            if requestor and hasattr(requestor, 'send'):
                try:
                    await requestor.send(f"Missing permission(s) in #{player.home.name}: {', '.join(missing)}. Please grant the bot these permissions.")
                except Exception:
                    pass
            return
        try:
            await player.home.send(view=view)
        except discord.Forbidden:
            requestor = getattr(player, 'last_requestor', None)
            if requestor and hasattr(requestor, 'send'):
                await requestor.send(f"Missing permission: Send Messages in #{player.home.name}. Please grant the bot this permission.")
        player.filters.reset()
        await player.disconnect()    
    
    @commands.Cog.listener()
    async def on_voltricx_node_disconnected(self, node: voltricx.Node) -> None:
        print(f"\033[93m[INFO] Node Disconnected\033[0m: {node.identifier}")

    @commands.Cog.listener()
    async def on_voltricx_node_ready(self, node: voltricx.Node) -> None:
        print(f"\033[92m[INFO] Node Ready\033[0m: {node.identifier}")

    @commands.Cog.listener()
    async def on_voltricx_track_exception(self, player: LavaMusic, track: voltricx.Playable, exception: Any):
        """Handle track exceptions during playback"""
        try:
            print(f"\033[91m[ERROR] Track Exception\033[0m: {exception.message} - Track: {track.title} (Source: {track.source})")

            # Skip to next track silently — load_failed / unavailable tracks
            # should not spam the user with error embeds.
            if not player.queue.is_empty:
                try:
                    next_track = player.queue.get()
                    await player.play(next_track, replace=True)
                except Exception as e:
                    await self.handle_voltricx_exception(e, "Track Exception - Skip")
            # Only notify if the error is NOT a routine YouTube unavailability
            msg = str(exception.message or "")
            is_unavailable = (
                "All clients failed" in msg
                or "This video is not available" in msg
                or "This video requires login" in msg
                or "Invalid status code" in msg
            )
            if is_unavailable:
                return

            # Build a safe, length-capped description
            cause = str(exception.cause or "")[:300]
            severity = str(exception.severity or "")[:50]
            short_msg = msg[:300]
            title = (track.title or "Unknown")[:200]
            author = (track.author or "Unknown")[:100]
            description = (
                f"An error occurred while playing **{title}**\n\n"
                f"**Cause:** {cause}\n"
                f"**Severity:** {severity}\n"
                f"**Message:** {short_msg or 'None'}\n\n"
                f"---\nTrack by {author}"
            )[:3900]  # hard cap well under Discord's 4000 limit

            try:
                if player.home:
                    await player.home.send(view=vx_design.track_error(description))
            except Exception as e:
                await self.handle_voltricx_exception(e, "Track Exception - Notification")

        except Exception as e:
            await self.handle_voltricx_exception(e, "Track Exception Handler")

    async def handle_voltricx_exception(self, exception: Exception, context: str = ""):
        """Centralized handler for all Voltricx exceptions"""
        try:
            if isinstance(exception, voltricx.VoltricxException):
                print(f"\033[91m[ERROR] Voltricx Exception\033[0m: {context} - {type(exception).__name__}: {exception}")
                
                if isinstance(exception, voltricx.NodeException):
                    print(f"\033[91m[ERROR] Node Exception\033[0m: {context} - {exception}")
                
                elif isinstance(exception, voltricx.InvalidClientException):
                    print(f"\033[91m[ERROR] Invalid Client Exception\033[0m: {context} - {exception}")
                
                elif isinstance(exception, voltricx.AuthorizationFailedException):
                    print(f"\033[91m[ERROR] Authorization Failed\033[0m: {context} - {exception}")
                
                elif isinstance(exception, voltricx.InvalidNodeException):
                    print(f"\033[91m[ERROR] Invalid Node Exception\033[0m: {context} - {exception}")
                
                elif isinstance(exception, voltricx.LavalinkException):
                    status = getattr(exception, "status", "Unknown")
                    error = getattr(exception, "error", "Unknown")
                    print(f"\033[91m[ERROR] Lavalink Exception\033[0m: {context} - Status: {status}, Error: {error}")
                
                elif isinstance(exception, voltricx.LavalinkLoadException):
                    print(f"\033[91m[ERROR] Lavalink Load Exception\033[0m: {context} - {exception}")
                
                elif isinstance(exception, voltricx.InvalidChannelStateException):
                    print(f"\033[91m[ERROR] Invalid Channel State\033[0m: {context} - {exception}")
                
                elif isinstance(exception, voltricx.ChannelTimeoutException):
                    print(f"\033[91m[ERROR] Channel Timeout\033[0m: {context} - {exception}")
                
                elif isinstance(exception, voltricx.QueueEmpty):
                    print(f"\033[93m[INFO] Queue Empty\033[0m: {context} - {exception}")
                
                else:
                    print(f"\033[91m[ERROR] Unknown voltricx Exception\033[0m: {context} - {type(exception).__name__}: {exception}")
            
            else:
                print(f"\033[91m[ERROR] Non-voltricx Exception\033[0m: {context} - {type(exception).__name__}: {exception}")
                
        except Exception as e:
            print(f"\033[91m[ERROR] Exception Handler Error\033[0m: {e}")  # Avoid recursion

    
    @commands.Cog.listener()
    async def on_voltricx_track_stuck(self, player: LavaMusic, track: voltricx.Playable, threshold: int):
        """Handle when a track gets stuck during playback"""
        try:
            print(f"\033[91m[ERROR] Track Stuck\033[0m: {track.title} - Threshold: {threshold}ms")
            
            # Get metadata for user notification
            metadata = player.metadata.get(track, {})
            requestor = metadata.get("requestor", None)
            
            try:
                if player.home:
                    await player.home.send(view=vx_design.track_stuck(track.title, track.author, threshold))
            except Exception as e:
                await self.handle_voltricx_exception(e, "Track Stuck - Notification")
                if requestor and hasattr(requestor, 'send'):
                    try:
                        await requestor.send(view=vx_design.track_stuck(track.title, track.author, threshold))
                    except Exception:
                        pass
            
            # Skip to next track if available
            if not player.queue.is_empty:
                try:
                    next_track = player.queue.get()
                    await player.play(next_track, replace=True)
                except Exception as e:
                    await self.handle_voltricx_exception(e, "Track Stuck - Skip")
                    
        except Exception as e:
            await self.handle_voltricx_exception(e, "Track Stuck Handler")

    @commands.Cog.listener()
    async def on_voltricx_websocket_closed(self, player: LavaMusic, code: int, reason: str, by_remote: bool):
        """Handle when websocket to voice server is closed"""
        try:
            print(f"\033[91m[ERROR] Websocket Closed\033[0m: Code {code} - Reason: {reason} - By Remote: {by_remote}")
            # Lavalink handles its own websocket reconnect internally — do NOT call
            # voice_client.disconnect() here. Disconnecting on every voice server
            # hiccup is what caused bots to leave VC during Discord instability.
        except Exception as e:
            await self.handle_voltricx_exception(e, "Websocket Closed Handler")

    @commands.Cog.listener()
    async def on_voltricx_node_closed(self, node: voltricx.Node, disconnected: list[voltricx.Player]):
        """Handle when a node is closed and players are disconnected"""
        try:
            print(f"\033[91m[ERROR] Node Closed\033[0m: Node {node.identifier} - Disconnected {len(disconnected)} players")

            for player in disconnected:
                # Clean up player_messages so dict doesn't leak on abnormal disconnect
                self.player_messages.pop(player, None)
                try:
                    if hasattr(player, 'home') and player.home:
                        try:
                            await player.home.send(view=vx_design.node_disconnected())
                        except Exception as e:
                            await self.handle_voltricx_exception(e, "Node Closed - Notification")

                except Exception as e:
                    await self.handle_voltricx_exception(e, "Node Closed - Player Notification")

        except Exception as e:
            await self.handle_voltricx_exception(e, "Node Closed Handler")



async def setup(bot):
    await bot.add_cog(Voltricx_Event(bot))
