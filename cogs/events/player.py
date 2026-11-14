import asyncpg
import discord
from discord.ext import commands
from discord.ui import Button
import voltricx
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.user_favorite import add_favorite
from utils.helper_function.unified_cache_manager import unified_cache
from emojis import (
    PLAY, SETTINGS, PAUSE, PLAYING, NEXT, PREV, STOP, FAVORITE,
    YOUTUBE, YTMUSIC, SPOTIFY, JIOSAAVN, SOUNDCLOUD, DEEZER, APPLE_MUSIC, YTDLP
)
import os
from dotenv import load_dotenv
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import player_card as pc_design
from utils.embed_designs import error_handler as err_design
from utils.check_decorators.dj_checker import dj_check_member
from utils.helper_function.session_manager import session_manager
from utils.embed_designs import session as session_design

load_dotenv()


class SettingsFilterSelect(discord.ui.Select):
    """Filter dropdown used inside the ephemeral SettingsView panel."""

    def __init__(self, player: "LavaMusic", settings_view: "SettingsView"):
        options = [
            discord.SelectOption(label="None",       value="reset",      description="Reset all filters"),
            discord.SelectOption(label="Bass Boost",  value="bass_boost"),
            discord.SelectOption(label="Nightcore",   value="nightcore"),
            discord.SelectOption(label="Vaporwave",   value="vaporwave"),
            discord.SelectOption(label="Karaoke",     value="karaoke"),
            discord.SelectOption(label="8D Audio",    value="8d_audio"),
            discord.SelectOption(label="Chipmunk",    value="chipmunk"),
            discord.SelectOption(label="Deep Voice",  value="deep_voice"),
        ]
        placeholder = (
            f"Filter: {player.filter_name}"
            if player.filter_status and player.filter_name and player.filter_name != "None"
            else "Select an Audio Filter…"
        )
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
        self.player = player
        self.settings_view = settings_view

    async def callback(self, interaction: discord.Interaction):
        if not session_manager.is_allowed(interaction.guild.id, interaction.user):
            info = session_manager.get_info(interaction.guild.id)
            owner_name = info.owner_name if info else "a DJ"
            await interaction.response.send_message(
                view=session_design.session_locked(owner_name), ephemeral=True
            )
            return

        allowed, role_id = await dj_check_member(interaction.user, interaction.guild)
        if not allowed:
            role = interaction.guild.get_role(role_id) if (interaction.guild and role_id) else None
            await interaction.response.send_message(
                view=err_design.dj_role_required(role.name if role else None), ephemeral=True
            )
            return

        filter_type = self.values[0]
        filters: voltricx.Filters = self.player.filters

        if filter_type == "reset":
            filters.reset()
            self.player.filter_name = "None"
            self.player.filter_status = False
        else:
            filters.reset()
            if filter_type == "nightcore":
                filters.timescale.set(speed=1.3, pitch=1.2, rate=1)
                self.player.filter_name = "NightCore"
            elif filter_type == "vaporwave":
                filters.timescale.set(speed=0.85, pitch=0.8, rate=1)
                filters.rotation.set(rotation_hz=0.2)
                self.player.filter_name = "VaporWave"
            elif filter_type == "karaoke":
                filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220, filter_width=100)
                self.player.filter_name = "Karaoke"
            elif filter_type == "8d_audio":
                filters.rotation.set(rotation_hz=0.12)
                self.player.filter_name = "8D"
            elif filter_type == "chipmunk":
                filters.timescale.set(speed=1.05, pitch=1.8, rate=1)
                self.player.filter_name = "ChipMunk"
            elif filter_type == "deep_voice":
                filters.timescale.set(speed=1.0, pitch=0.6, rate=1)
                self.player.filter_name = "Deep Voice"
            elif filter_type == "bass_boost":
                filters.equalizer.set(
                    bands=[
                        {"band": 0,  "gain": 0.075},   {"band": 1,  "gain": 0.08375},
                        {"band": 2,  "gain": 0.08375},  {"band": 3,  "gain": 0.05},
                        {"band": 4,  "gain": -0.0625},  {"band": 5,  "gain": 0.01875},
                        {"band": 6,  "gain": -0.05625}, {"band": 7,  "gain": 0.02875},
                        {"band": 8,  "gain": 0.04375},  {"band": 9,  "gain": 0.05625},
                        {"band": 10, "gain": 0.06875},  {"band": 11, "gain": -0.075},
                        {"band": 12, "gain": 0.06875},  {"band": 13, "gain": -0.0625},
                        {"band": 14, "gain": -0.09375},
                    ]
                )
                self.player.filter_name = "Bass Boost"
            self.player.filter_status = True

        await self.player.set_filters(filters)
        await self.settings_view._refresh_panel(interaction)


class SettingsView(discord.ui.LayoutView):
    """
    Rich ephemeral settings panel opened when the ⚙️ gear button is clicked.

    Layout (inside a single accent-colored Container):
    ┌────────────────────────────────────────────────────────────┐
    │  ## ⚙️ Player Settings                                     │
    │  ────────────────────────────────────────────────────────  │
    │  Current track title               [ artwork thumbnail ]   │
    │  Vol · Queue · Loop · AutoPlay · Filter                    │
    │  ────────────────────────────────────────────────────────  │
    │  🔁 Loop Mode                                              │
    │  [ Normal ]  [ Loop Track ]  [ Loop Queue ]                │
    │                                                            │
    │  ▶ AutoPlay  ·  🔀 Queue                                  │
    │  [ AutoPlay: On/Off ]  [ 🔀 Shuffle Queue ]               │
    │                                                            │
    │  🔊 Volume — 60%                                           │
    │  [ -25 ] [ -10 ] [ Reset ] [ +10 ] [ +25 ]               │
    │                                                            │
    │  🎚️ Audio Filter                                           │
    │  [ Filter dropdown ]                                       │
    └────────────────────────────────────────────────────────────┘
    """

    def __init__(self, player: "LavaMusic", main_view: "PlayerView"):
        super().__init__(timeout=120)
        self.player = player
        self.main_view = main_view
        self._setup_components()
        self._build_ui()

    # ── component creation (called once) ──────────────────────────────────────

    def _setup_components(self):
        # --- Loop mode row ---
        self.loop_row = discord.ui.ActionRow()
        self.loop_normal_btn = Button(label="Normal",     style=discord.ButtonStyle.secondary)
        self.loop_track_btn  = Button(label="Loop Track", style=discord.ButtonStyle.secondary)
        self.loop_queue_btn  = Button(label="Loop Queue", style=discord.ButtonStyle.secondary)
        self.loop_normal_btn.callback = self._loop_normal_callback
        self.loop_track_btn.callback  = self._loop_track_callback
        self.loop_queue_btn.callback  = self._loop_queue_callback
        self.loop_row.add_item(self.loop_normal_btn)
        self.loop_row.add_item(self.loop_track_btn)
        self.loop_row.add_item(self.loop_queue_btn)

        # --- AutoPlay + Shuffle row ---
        self.misc_row = discord.ui.ActionRow()
        self.autoplay_btn = Button(label="AutoPlay: Off", style=discord.ButtonStyle.secondary)
        self.shuffle_btn  = Button(label="🔀 Shuffle Queue", style=discord.ButtonStyle.primary)
        self.autoplay_btn.callback = self._autoplay_callback
        self.shuffle_btn.callback  = self._shuffle_callback
        self.misc_row.add_item(self.autoplay_btn)
        self.misc_row.add_item(self.shuffle_btn)

        # --- Volume row ---
        self.vol_row = discord.ui.ActionRow()
        self.v_m25   = Button(label="-25",      style=discord.ButtonStyle.secondary)
        self.v_m10   = Button(label="-10",      style=discord.ButtonStyle.secondary)
        self.v_reset = Button(label="Reset Vol", style=discord.ButtonStyle.primary)
        self.v_p10   = Button(label="+10",      style=discord.ButtonStyle.secondary)
        self.v_p25   = Button(label="+25",      style=discord.ButtonStyle.secondary)
        self.v_m25.callback   = lambda i: self._vol_adjust(i, -25)
        self.v_m10.callback   = lambda i: self._vol_adjust(i, -10)
        self.v_reset.callback = self._vol_reset
        self.v_p10.callback   = lambda i: self._vol_adjust(i, 10)
        self.v_p25.callback   = lambda i: self._vol_adjust(i, 25)
        self.vol_row.add_item(self.v_m25)
        self.vol_row.add_item(self.v_m10)
        self.vol_row.add_item(self.v_reset)
        self.vol_row.add_item(self.v_p10)
        self.vol_row.add_item(self.v_p25)

        # --- Filter row ---
        self.filter_row = discord.ui.ActionRow()
        self.settings_filter_select = SettingsFilterSelect(self.player, self)
        self.filter_row.add_item(self.settings_filter_select)

    # ── state sync (called before every rebuild) ──────────────────────────────

    def _sync_button_states(self):
        mode = self.player.queue.mode
        self.loop_normal_btn.style = (
            discord.ButtonStyle.success if mode == voltricx.QueueMode.normal
            else discord.ButtonStyle.secondary
        )
        self.loop_track_btn.style = (
            discord.ButtonStyle.success if mode == voltricx.QueueMode.loop
            else discord.ButtonStyle.secondary
        )
        self.loop_queue_btn.style = (
            discord.ButtonStyle.success if mode == voltricx.QueueMode.loop_all
            else discord.ButtonStyle.secondary
        )

        is_ap = self.player.autoplay == voltricx.AutoPlayMode.enabled
        self.autoplay_btn.label = "AutoPlay: On" if is_ap else "AutoPlay: Off"
        self.autoplay_btn.style = (
            discord.ButtonStyle.success if is_ap else discord.ButtonStyle.secondary
        )

        # Disable shuffle if queue is too small
        self.shuffle_btn.disabled = len(self.player.queue) < 2

        # Clamp volume buttons so they can't go out of range
        self.v_m25.disabled = self.player.volume <= 1
        self.v_m10.disabled = self.player.volume <= 1
        self.v_p10.disabled = self.player.volume >= 100
        self.v_p25.disabled = self.player.volume >= 100

        # Update filter select placeholder
        self.settings_filter_select.placeholder = (
            f"Filter: {self.player.filter_name}"
            if self.player.filter_status and self.player.filter_name and self.player.filter_name != "None"
            else "Select an Audio Filter…"
        )

    # ── layout builder ────────────────────────────────────────────────────────

    def _build_ui(self):
        self.clear_items()
        self._sync_button_states()
        container = pc_design.build_settings_container(
            self.player.volume,
            self.loop_row,
            self.misc_row,
            self.vol_row,
            self.filter_row,
        )
        self.add_item(container)

    # ── shared refresh helper ─────────────────────────────────────────────────

    async def _refresh_panel(self, interaction: discord.Interaction):
        """Rebuild settings panel in place."""
        self._build_ui()
        await interaction.response.edit_message(view=self)

    # ── loop callbacks ────────────────────────────────────────────────────────

    async def _loop_normal_callback(self, interaction: discord.Interaction):
        self.player.queue.mode = voltricx.QueueMode.normal
        await self._refresh_panel(interaction)

    async def _loop_track_callback(self, interaction: discord.Interaction):
        self.player.queue.mode = voltricx.QueueMode.loop
        await self._refresh_panel(interaction)

    async def _loop_queue_callback(self, interaction: discord.Interaction):
        self.player.queue.mode = voltricx.QueueMode.loop_all
        await self._refresh_panel(interaction)

    # ── autoplay / shuffle callbacks ──────────────────────────────────────────

    async def _autoplay_callback(self, interaction: discord.Interaction):
        if self.player.autoplay == voltricx.AutoPlayMode.enabled:
            self.player._autoplay = voltricx.AutoPlayMode.partial
        else:
            self.player._autoplay = voltricx.AutoPlayMode.enabled
        await self._refresh_panel(interaction)

    async def _shuffle_callback(self, interaction: discord.Interaction):
        allowed, role_id = await dj_check_member(interaction.user, interaction.guild)
        if not allowed:
            role = interaction.guild.get_role(role_id) if (interaction.guild and role_id) else None
            await interaction.response.send_message(
                view=err_design.dj_role_required(role.name if role else None), ephemeral=True
            )
            return
        self.player.queue.shuffle()
        await self._refresh_panel(interaction)

    # ── volume callbacks ──────────────────────────────────────────────────────

    async def _vol_adjust(self, interaction: discord.Interaction, change: int):
        new_vol = max(1, min(100, self.player.volume + change))
        await self.player.set_volume(new_vol)
        self.main_view.current_vol = new_vol
        await self._refresh_panel(interaction)

    async def _vol_reset(self, interaction: discord.Interaction):
        await self.player.set_volume(50)
        self.main_view.current_vol = 50
        await self._refresh_panel(interaction)


class PlayerView(discord.ui.LayoutView):
    def __init__(self, bot, player: LavaMusic, requestor: discord.Member, track, formatted_duration, platform):
        super().__init__()
        self.timeout = None
        self.bot = bot
        self.player = player
        self.requestor = requestor
        self.track = track
        self.formatted_duration = formatted_duration
        self.platform = platform
        self.history_index = 0
        self.current_vol = player.volume
        self.player.interaction_view = self
        
        # Store UI state
        source_lower = str(platform).lower()
        self.platform_emoji = ""
        if "youtube" in source_lower: 
            self.platform_emoji = YTMUSIC if "music" in source_lower else YOUTUBE
        elif "spotify" in source_lower: 
            self.platform_emoji = SPOTIFY
        elif "jiosaavn" in source_lower or "js" in source_lower: 
            self.platform_emoji = JIOSAAVN
        elif "soundcloud" in source_lower: 
            self.platform_emoji = SOUNDCLOUD
        elif "deezer" in source_lower or "dz" in source_lower: 
            self.platform_emoji = DEEZER
        elif "apple" in source_lower: 
            self.platform_emoji = APPLE_MUSIC
        elif "ytdl" in source_lower: 
            self.platform_emoji = YTDLP
            
        self.header_text = f" ## **Playing on {platform}** {self.platform_emoji}"
        
        # Initialize persistent rows and buttons
        self._setup_components()
        self._build_ui()

    def _setup_components(self):
        # Control buttons row 1
        self.control_row_1 = discord.ui.ActionRow()
        
        self.prev_button = Button(emoji=PREV, style=discord.ButtonStyle.secondary)
        self.prev_button.callback = self.prev_callback
        
        self.play_pause_button = Button(
            emoji=PAUSE if not self.player.paused else PLAY, 
            style=discord.ButtonStyle.secondary
        )
        self.play_pause_button.callback = self.play_pause_callback
        
        self.next_button = Button(emoji=NEXT, style=discord.ButtonStyle.secondary)
        self.next_button.callback = self.next_callback
        
        self.stop_button = Button(emoji=STOP, style=discord.ButtonStyle.danger)
        self.stop_button.callback = self.stop_callback

        self.settings_button = Button(emoji=SETTINGS, style=discord.ButtonStyle.secondary)
        self.settings_button.callback = self.settings_callback
        
        self.control_row_1.add_item(self.prev_button)
        self.control_row_1.add_item(self.play_pause_button)
        self.control_row_1.add_item(self.next_button)
        self.control_row_1.add_item(self.stop_button)
        self.control_row_1.add_item(self.settings_button)
        
        # Control buttons row 2
        self.control_row_2 = discord.ui.ActionRow()
        
        self.fav_button = Button(label=" Add To Favs", emoji=FAVORITE, style=discord.ButtonStyle.secondary)
        self.fav_button.callback = self.fav_callback
        
        self.control_row_2.add_item(self.fav_button)

    def _build_ui(self):
        self.clear_items()

        self.current_vol = self.player.volume
        self.play_pause_button.emoji = PAUSE if not self.player.paused else PLAY

        track_info_content = pc_design.track_info_text(
            PLAYING,
            self.track.title,
            self.track.uri,
            self.track.author,
            self.formatted_duration,
            self.requestor.display_name,
        )
        self.container = pc_design.build_player_container(
            self.header_text,
            track_info_content,
            self.track.artwork,
            self.control_row_1,
            self.control_row_2,
        )
        self.add_item(self.container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if await self._is_user_blacklisted(interaction.user.id):
            return False

        if interaction.user.voice is None:
            await interaction.response.send_message(view=pc_design.not_in_voice(), ephemeral=True)
            return False

        if self.player is None or interaction.user.voice.channel != self.player.channel:
            await interaction.response.send_message(view=pc_design.different_voice(), ephemeral=True)
            return False

        # "Add to Favs" is personal and doesn't affect playback — allow it even in locked sessions.
        # All other buttons (prev, play/pause, next, stop, settings) are music controls.
        is_fav_button = (
            interaction.data.get("custom_id") == self.fav_button.custom_id
            if hasattr(self, "fav_button") and self.fav_button.custom_id
            else False
        )
        if not is_fav_button and not session_manager.is_allowed(interaction.guild.id, interaction.user):
            info = session_manager.get_info(interaction.guild.id)
            owner_name = info.owner_name if info else "a DJ"
            await interaction.response.send_message(
                view=session_design.session_locked(owner_name), ephemeral=True
            )
            return False

        return True

    async def _is_user_blacklisted(self, user_id: int) -> bool:
        try:
            return await unified_cache.is_user_blacklisted(user_id)
        except Exception as e:
            print(f"Blacklist check error: {e}")
            return False

    async def prev_callback(self, interaction: discord.Interaction):
        history = list(reversed(self.player.queue.history))
        if not history:
            return await interaction.response.send_message(view=pc_design.no_previous_track(), ephemeral=True)

        if self.history_index >= len(history):
            self.history_index = 0
            return await interaction.response.send_message(view=pc_design.history_reset(), ephemeral=True)
            
        previous_track = history[self.history_index]
        self.history_index += 1
        await self.player.play(previous_track, replace=True, add_history=False)
        if self.player.paused:
            await self.player.pause(False)
        await interaction.response.defer()

    async def update_ui(self):
        if hasattr(self.player, 'msg') and self.player.msg:
            try:
                self._build_ui()
                await self.player.msg.edit(view=self)
            except Exception as e:
                print(f"Error updating UI: {e}")

    async def play_pause_callback(self, interaction: discord.Interaction):
        if self.player.paused:
            await self.player.pause(False)
        else:
            await self.player.pause(True)
            
        self._build_ui()
        await interaction.response.edit_message(view=self)

    async def next_callback(self, interaction: discord.Interaction):
        await self.player.skip()
        if self.player.paused:
            await self.player.pause(False)
        self.history_index = 0
        await interaction.response.defer()

    async def stop_callback(self, interaction: discord.Interaction):
        from utils.helper_function.autoplay_cache import autoplay_cache
        from cogs.commands.playlist import stop_playlist_session
        autoplay_cache.stop_session(self.player.guild.id)
        stop_playlist_session(self.player.guild.id)
        self.player.filter_name = "None"
        self.player.filter_status = False
        self.player.filters.reset()
        self.player.queue.clear()
        self.player._autoplay = voltricx.AutoPlayMode.partial
        await self.player.stop()
        await interaction.response.send_message(view=pc_design.player_stopped(interaction.user.mention))
        await self.player.disconnect()

    async def settings_callback(self, interaction: discord.Interaction):
        settings_view = SettingsView(player=self.player, main_view=self)
        await interaction.response.send_message(view=settings_view, ephemeral=True)

    async def fav_callback(self, interaction: discord.Interaction):
        track = self.player.current
        if not track:
            return await interaction.response.send_message(view=pc_design.no_track_playing(), ephemeral=True)

        try:
            await add_favorite(interaction.user.id, track.uri, track.title)
            view = pc_design.favorite_added(track.title, track.uri)
        except Exception as e:
            view = pc_design.favorite_error(str(e))

        await interaction.response.send_message(view=view, ephemeral=True)

    def _get_track_info_content(self):
        return pc_design.track_info_text(
            PLAYING,
            self.track.title,
            self.track.uri,
            self.track.author,
            self.formatted_duration,
            self.requestor.display_name,
        )


class PlayerCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_controls_status(self, guild_id: int) -> bool:
        try:
            bot_id = self.bot.user.id
            return await unified_cache.is_hide_controls_enabled(guild_id, bot_id)
        except Exception as e:
            print(f"Controls status check error: {e}")
            return False

    async def send_track_embed(self, player: LavaMusic, track, formatted_duration, requestor, platform, icon_url):
        try:
            controls_hidden = await self._get_controls_status(player.guild.id)
            
            view = PlayerView(self.bot, player, requestor, track, formatted_duration, platform)
            
            if controls_hidden:
                source_lower = str(platform).lower()
                platform_emoji = ""
                if "youtube" in source_lower:
                    platform_emoji = YTMUSIC if "music" in source_lower else YOUTUBE
                elif "spotify" in source_lower:
                    platform_emoji = SPOTIFY
                elif "jiosaavn" in source_lower or "js" in source_lower:
                    platform_emoji = JIOSAAVN
                elif "soundcloud" in source_lower:
                    platform_emoji = SOUNDCLOUD
                elif "deezer" in source_lower or "dz" in source_lower:
                    platform_emoji = DEEZER
                elif "apple" in source_lower:
                    platform_emoji = APPLE_MUSIC
                elif "ytdl" in source_lower:
                    platform_emoji = YTDLP

                header_text = f"**Playing on {platform}** {platform_emoji} "
                autoplay_on = player.autoplay == voltricx.AutoPlayMode.enabled
                if player.queue.mode == voltricx.QueueMode.loop:
                    loop_text = "\n> Loop : **Track** 🔂"
                elif player.queue.mode == voltricx.QueueMode.loop_all:
                    loop_text = "\n> Loop : **Queue** 🔁"
                else:
                    loop_text = ""
                filter_text = f"\n> Filter : **{player.filter_name}**" if player.filter_status else ""

                track_info_content = pc_design.track_info_text_full(
                    PLAYING,
                    track.title,
                    track.uri,
                    track.author,
                    formatted_duration,
                    requestor.display_name,
                    player.volume,
                    autoplay_on,
                    loop_text,
                    filter_text,
                )
                new_container = pc_design.build_controls_hidden_container(
                    header_text, track_info_content, track.artwork
                )
                view.clear_items()
                view.add_item(new_container)
                view.container = new_container

            player.msg = await player.home.send(view=view)
            return player.msg.id
        except Exception as e:
            print(f"Error sending track info: {e}")
            if player.home:
                await player.home.send(f"Error sending track info: {e}")


async def setup(bot):
    await bot.add_cog(PlayerCard(bot))