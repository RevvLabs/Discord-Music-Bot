from discord.ext import commands
from utils.logger.mewzik_logger import bot_logger
from utils.embed_designs import voice_check as vc_design
from utils.helper_function.session_manager import session_manager
from utils.embed_designs import session as session_design


async def ensure_voice(ctx: commands.Context):
    if not ctx.author.voice or not ctx.author.voice.channel:
        if bot_logger.enabled:
            bot_logger.incoming(
                "ensure_voice — user not in any voice channel",
                user_id=ctx.author.id,
                user=str(ctx.author),
                guild_id=ctx.guild.id,
            )
        await ctx.send(view=vc_design.not_in_voice(), ephemeral=True)
        return False

    if not ctx.guild.voice_client:
        if bot_logger.enabled:
            bot_logger.incoming(
                "ensure_voice — bot not connected to any voice channel",
                user_id=ctx.author.id,
                guild_id=ctx.guild.id,
            )
        await ctx.send(view=vc_design.bot_not_connected(), ephemeral=True)
        return False

    if ctx.guild.voice_client.channel != ctx.author.voice.channel:
        if bot_logger.enabled:
            bot_logger.incoming(
                "ensure_voice — user in different voice channel than bot",
                user_id=ctx.author.id,
                user_channel=ctx.author.voice.channel.name,
                bot_channel=ctx.guild.voice_client.channel.name,
                guild_id=ctx.guild.id,
            )
        await ctx.send(view=vc_design.different_voice(), ephemeral=True)
        return False

    # Session lock check — runs last so voice checks still give their own errors
    if not session_manager.is_allowed(ctx.guild.id, ctx.author):
        info = session_manager.get_info(ctx.guild.id)
        owner_name = info.owner_name if info else "a DJ"
        await ctx.send(view=session_design.session_locked(owner_name), ephemeral=True)
        return False

    return True
