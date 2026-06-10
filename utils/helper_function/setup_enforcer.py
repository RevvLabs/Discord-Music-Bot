from utils.helper_function.unified_cache_manager import unified_cache
from utils.logger.mewzik_logger import bot_logger
from utils.embed_designs import setup_enforcer as se_design
from utils.embed_designs import temp_setup as ts_design


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

        if ctx.channel.id != text_channel_id:
            text_channel = ctx.guild.get_channel(text_channel_id)
            tc_mention = text_channel.mention if text_channel else f"<#{text_channel_id}>"
            if bot_logger.enabled:
                bot_logger.incoming(
                    "enforce_temp_setup — wrong text channel",
                    user_id=ctx.author.id,
                    user=str(ctx.author),
                    guild_id=ctx.guild.id,
                    used_channel_id=ctx.channel.id,
                    expected_channel_id=text_channel_id,
                )
            await ctx.reply(view=ts_design.wrong_channel(tc_mention))
            return False

        user_vc = ctx.author.voice.channel if ctx.author.voice else None
        if not user_vc or user_vc.category_id != category_id:
            category = ctx.guild.get_channel(category_id)
            cat_name = category.name if category else f"<#{category_id}>"
            if bot_logger.enabled:
                bot_logger.incoming(
                    "enforce_temp_setup — user not in required category",
                    user_id=ctx.author.id,
                    user=str(ctx.author),
                    guild_id=ctx.guild.id,
                    required_category_id=category_id,
                )
            await ctx.reply(view=ts_design.wrong_category(cat_name))
            return False

        if bot_logger.enabled:
            bot_logger.debug("enforce_temp_setup — passed", user_id=ctx.author.id, guild_id=ctx.guild.id)
        return True

    # --- no setup active ---
    if bot_logger.enabled:
        bot_logger.debug("enforce_setup — no config, passing through", guild_id=ctx.guild.id)
    return True
