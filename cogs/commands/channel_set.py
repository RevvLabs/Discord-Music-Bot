import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.admin_or_owner import admin_or_owner
from utils.embed_designs import channel_set as cs_design
from utils.embed_designs import temp_setup as ts_design
from utils.helper_function.auto_delete import schedule_delete
from utils.helper_function.unified_cache_manager import unified_cache

load_dotenv()


class SetChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_channels_from_db(self, guild_id, bot_id):
        data = await unified_cache.get_channel_set_data(guild_id, bot_id)
        if data:
            return (data["player_channel_id"], data["voice_channel_id"])
        return None

    async def set_channels_in_db(self, guild_id, bot_id, player_channel_id, voice_channel_id):
        await unified_cache.set_channel_set_data(guild_id, bot_id, player_channel_id, voice_channel_id)

    @commands.hybrid_command(name="setup", description="Set the player and voice channels for the guild.")
    @commands.cooldown(1, 5, BucketType.user)
    @admin_or_owner()
    @is_not_blacklisted()
    @maintenance_check()
    async def set_channels(self, ctx, text_channel: discord.TextChannel, voice_channel: discord.VoiceChannel):
        bot_id = self.bot.user.id
        temp_active = await unified_cache.get_temp_setup_data(ctx.guild.id, bot_id)
        if temp_active:
            return schedule_delete(await ctx.send(view=ts_design.conflict_temp(), ephemeral=True))
        await self.set_channels_in_db(ctx.guild.id, bot_id, text_channel.id, voice_channel.id)
        schedule_delete(await ctx.send(view=cs_design.setup_done(text_channel.mention, voice_channel.mention)))

    @commands.hybrid_command(name="clearsetup", description="Clear the player and voice channel setup for the guild.")
    @commands.cooldown(1, 5, BucketType.user)
    @admin_or_owner()
    @is_not_blacklisted()
    @maintenance_check()
    async def clear_setup(self, ctx):
        await unified_cache.delete_channel_set_data(ctx.guild.id, self.bot.user.id)
        schedule_delete(await ctx.send(view=cs_design.setup_cleared()))

    @commands.hybrid_command(name="getsetup", description="Get the player and voice channels for the guild.")
    @commands.cooldown(1, 5, BucketType.user)
    @admin_or_owner()
    @is_not_blacklisted()
    @maintenance_check()
    async def get_channels(self, ctx):
        result = await self.get_channels_from_db(ctx.guild.id, self.bot.user.id)
        if result:
            player_channel_id, voice_channel_id = result
            player_channel = self.bot.get_channel(player_channel_id)
            voice_channel = self.bot.get_channel(voice_channel_id)
            pc_mention = player_channel.mention if player_channel else f"<#{player_channel_id}> (deleted?)"
            vc_mention = voice_channel.mention if voice_channel else f"<#{voice_channel_id}> (deleted?)"
            schedule_delete(await ctx.send(view=cs_design.current_setup(pc_mention, vc_mention)))
        else:
            schedule_delete(await ctx.send(view=cs_design.no_setup()))

async def setup(bot):
    await bot.add_cog(SetChannels(bot))
