"""Single owner of music-session teardown.

A "music session" starts when a track starts (``player.session_active = True``,
set in ``on_voltricx_track_start``) and ends exactly once, whichever happens first:

* queue / autoplay / playlist exhausted     -> on_voltricx_track_end
* every human left the bot's voice channel  -> AutoStop (cogs/events/alone.py)
* player idle past ``inactive_timeout``      -> on_voltricx_inactive_player
* /stop, stop button, /disconnect            -> the command itself (notify=False)
* bot kicked / disconnected / player killed  -> on_mewzik_player_destroyed

``end_session`` is idempotent (guarded by ``player.session_active``) so every
path can call it without double "Session Over" messages or double cleanup.
"""
import discord
import voltricx

from utils.helper_function.autoplay_cache import autoplay_cache
from utils.helper_function.unified_cache_manager import unified_cache
from utils.helper_function.session_manager import session_manager
from utils.embed_designs import session as session_design


async def is_247_enabled(bot, guild_id: int) -> bool:
    """/setup guilds keep the bot in the setup VC permanently (24/7 mode)."""
    bot_id = bot.user.id if bot.user else 0
    return await unified_cache.get_channel_set_data(guild_id, bot_id) is not None


def reset_player_state(player) -> None:
    """Drop queued tracks and per-session player settings (loop, filters, autoplay)."""
    if isinstance(player.queue, voltricx.Queue):
        player.queue.mode = voltricx.QueueMode.normal
    player.queue.clear()
    player.filters.reset()
    player.filter_name = "None"
    player.filter_status = False
    player._autoplay = voltricx.AutoPlayMode.partial  # autoplay has no setter


async def end_session(player, *, reason: str = "finished", notify: bool = True) -> bool:
    """End the player's music session once. Returns False if it was already ended."""
    if player is None or not getattr(player, "session_active", False):
        return False
    player.session_active = False

    guild = player.guild
    if guild is not None:
        from cogs.commands.playlist import stop_playlist_session
        autoplay_cache.stop_session(guild.id)
        stop_playlist_session(guild.id)
        session_manager.unlock(guild.id)

    channel = player.channel
    if channel:
        try:
            await channel.edit(status="Ready To Play !")
        except (discord.DiscordException, AttributeError):
            pass

    card = getattr(player, "msg", None)
    player.msg = None
    if card is not None:
        try:
            await card.delete()
        except discord.DiscordException:
            pass

    home = getattr(player, "home", None)
    if notify and home is not None:
        try:
            await home.send(view=session_design.session_over(reason))
        except discord.DiscordException:
            pass
    return True
