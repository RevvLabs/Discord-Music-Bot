from utils.helper_function.unified_cache_manager import unified_cache
from utils.logger.mewzik_logger import bot_logger
from utils.embed_designs import setup_enforcer as se_design
from utils.embed_designs import temp_setup as ts_design
from utils.helper_function import temp_noprefix

# Commands that may CLAIM a VC for a temp bot (cause a join). Others require an
# existing assignment — mirrors the no-prefix join-class set.
_TEMP_JOIN_COMMANDS = {"play", "p", "search", "join"}


async def get_channels_from_db(guild_id, bot_id=0):
    channel_data = await unified_cache.get_channel_set_data(guild_id, bot_id)
    if channel_data:
        return (channel_data["player_channel_id"], channel_data["voice_channel_id"])
    return None

async def enforce_setup(ctx, embed_color=None):
    bot_id = ctx.bot.user.id if ctx.bot.user else 0

    # --- standard setup ---
    result = await get_channels_from_db(ctx.guild.id, bot_id)
    if result:
        player_channel_id, voice_channel_id = result
        player_channel = ctx.guild.get_channel(player_channel_id)
        voice_channel = ctx.guild.get_channel(voice_channel_id)

        if ctx.channel.id != player_channel_id:
            if bot_logger.enabled:
                bot_logger.incoming(
                    "enforce_setup — wrong text channel",
                    user_id=ctx.author.id,
                    user=str(ctx.author),
                    guild_id=ctx.guild.id,
                    used_channel_id=ctx.channel.id,
                    expected_channel_id=player_channel_id,
                )
            if player_channel:
                await ctx.reply(view=se_design.wrong_channel(player_channel.mention))
            return False

        if not ctx.author.voice or ctx.author.voice.channel.id != voice_channel_id:
            if bot_logger.enabled:
                bot_logger.incoming(
                    "enforce_setup — user not in required voice channel",
                    user_id=ctx.author.id,
                    user=str(ctx.author),
                    guild_id=ctx.guild.id,
                    required_voice_channel_id=voice_channel_id,
                )
            vc_mention = voice_channel.mention if voice_channel else f"<#{voice_channel_id}>"
            await ctx.reply(view=se_design.wrong_voice(vc_mention))
            return False

        if bot_logger.enabled:
            bot_logger.debug("enforce_setup — passed", user_id=ctx.author.id, guild_id=ctx.guild.id)
        return True

    # --- temp setup ---
    temp_data = await unified_cache.get_temp_setup_data(ctx.guild.id, bot_id)
    if temp_data:
        text_channel_id = temp_data["text_channel_id"]
        category_id = temp_data["category_id"]

        # Multiple temp bots all receive the same prefix command. Only the
        # "primary" bot (lowest temp bot id for this guild) replies to usage
        # errors, so users don't get N identical error messages.
        try:
            bot_ids = await unified_cache.get_temp_setup_bot_ids(ctx.guild.id)
            is_primary = bool(bot_ids) and bot_id == min(bot_ids)
        except Exception:
            is_primary = True

        # Text channel is no longer mandatory — any channel inside the temp
        # category works (the VC's own text chat or any category text channel).
        if getattr(ctx.channel, "category_id", None) != category_id:
            if is_primary:
                category = ctx.guild.get_channel(category_id)
                cat_name = category.name if category else f"<#{category_id}>"
                await ctx.reply(view=ts_design.wrong_category(cat_name))
            return False

        user_vc = ctx.author.voice.channel if ctx.author.voice else None
        if not user_vc or user_vc.category_id != category_id:
            if is_primary:
                category = ctx.guild.get_channel(category_id)
                cat_name = category.name if category else f"<#{category_id}>"
                await ctx.reply(view=ts_design.wrong_category(cat_name))
            return False

        # Ownership gate: only the bot that owns (or atomically claims) this VC
        # proceeds. Every other temp bot returns False SILENTLY — this is what
        # stops a 2nd bot joining a VC that's already served, including for
        # prefix commands (which all temp bots receive).
        is_join = bool(ctx.command and ctx.command.name in _TEMP_JOIN_COMMANDS)
        status = await temp_noprefix.decide_ownership(
            ctx.bot, ctx.guild, user_vc, is_join, text_channel_id=text_channel_id
        )
        if status != "mine":
            if bot_logger.enabled:
                bot_logger.debug(
                    "enforce_temp_setup — not this bot's VC, yielding",
                    guild_id=ctx.guild.id, vc_id=user_vc.id, bot_id=bot_id,
                )
            return False

        if bot_logger.enabled:
            bot_logger.debug("enforce_temp_setup — passed (owner)", user_id=ctx.author.id, guild_id=ctx.guild.id)
        return True

    # --- no setup active ---
    if bot_logger.enabled:
        bot_logger.debug("enforce_setup — no config, passing through", guild_id=ctx.guild.id)
    return True
