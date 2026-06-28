
from discord.ext import commands
import os
from dotenv import load_dotenv
from utils.helper_function.unified_cache_manager import unified_cache
from utils.check_decorators.dj_checker import dj_check_member
from utils.helper_function import temp_noprefix

load_dotenv()


async def _no_prefix_active(bot, message) -> bool:
    """
    Decide whether bare (prefix-less) commands should be accepted for this message.

    All of these must be true:
      • the message is in the guild's configured setup text/player channel
      • the author is currently in the configured setup voice channel
      • the bot is connected to that same setup voice channel
      • the author passes the DJ check (only enforced once a DJ role is set)

    Any failure (or missing setup) returns False so the bot simply falls back to
    the normal prefix — prefix-less text is then ignored in complete silence.
    """
    try:
        guild = message.guild
        bot_id = bot.user.id if bot.user else 0

        data = await unified_cache.get_channel_set_data(guild.id, bot_id)
        if not data:
            return False

        player_channel_id = data.get("player_channel_id")
        voice_channel_id = data.get("voice_channel_id")
        if not player_channel_id or not voice_channel_id:
            return False

        # 1. message must be in the setup text channel
        if message.channel.id != player_channel_id:
            return False

        # 2. author must be in the setup voice channel
        author_voice = getattr(message.author, "voice", None)
        if not author_voice or not author_voice.channel:
            return False
        if author_voice.channel.id != voice_channel_id:
            return False

        # 3. bot must be connected to that same setup voice channel
        vc = guild.voice_client
        if not vc or not vc.channel or vc.channel.id != voice_channel_id:
            return False

        # 4. author must pass the DJ check (no-op if no DJ role is configured)
        allowed, _ = await dj_check_member(message.author, guild)
        if not allowed:
            return False

        return True
    except Exception:
        return False


async def get_prefix(bot, message):
    if message.guild:
        bot_id = bot.user.id if bot.user else 0
        prefix = await unified_cache.get_prefix(message.guild.id, bot_id)
        if await _no_prefix_active(bot, message):
            # Empty prefix LAST so the real prefix is still matched first
            # (e.g. "-skip" resolves via "-", not via the empty prefix).
            return commands.when_mentioned_or(prefix, "")(bot, message)
        # Separate Temp Setup no-prefix system (isolated; only fires for temp bots).
        if await temp_noprefix.resolve(bot, message) == "":
            return commands.when_mentioned_or(prefix, "")(bot, message)
        return commands.when_mentioned_or(prefix)(bot, message)
    return commands.when_mentioned_or(os.getenv("PREFIX"))(bot, message)
