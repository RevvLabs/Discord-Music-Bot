import discord
from discord.ext import commands
from discord.ext.commands import BucketType

from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.embed_designs import temp_setup as ts_design
from utils.embed_designs import channel_set as cs_design
from utils.helper_function.auto_delete import schedule_delete
from utils.helper_function.unified_cache_manager import unified_cache


class TempSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="temp-setup", description="Restrict bot to a text channel and category. Mutually exclusive with /setup.")
    @commands.cooldown(1, 5, BucketType.user)
    @commands.has_permissions(administrator=True)
    @is_not_blacklisted()
    @maintenance_check()
    async def temp_setup(self, ctx, text_channel: discord.TextChannel, category: discord.CategoryChannel):
        bot_id = self.bot.user.id
        setup_active = await unified_cache.get_channel_set_data(ctx.guild.id, bot_id)
        if setup_active:
            return schedule_delete(await ctx.send(view=ts_design.conflict_setup(), ephemeral=True))

        ok = await unified_cache.set_temp_setup_data(ctx.guild.id, bot_id, text_channel.id, category.id)
        if ok:
            schedule_delete(await ctx.send(view=ts_design.setup_done(text_channel.mention, category.name)))
        else:
            await ctx.send("Failed to save temp setup.", ephemeral=True)

    @commands.hybrid_command(name="clear-tempsetup", description="Clear the temp setup for this server.")
    @commands.cooldown(1, 5, BucketType.user)
    @commands.has_permissions(administrator=True)
    @is_not_blacklisted()
    @maintenance_check()
    async def clear_temp_setup(self, ctx):
        bot_id = self.bot.user.id
        await unified_cache.delete_temp_setup_data(ctx.guild.id, bot_id)
        schedule_delete(await ctx.send(view=ts_design.setup_cleared()))

    @commands.hybrid_command(name="get-tempsetup", description="Show the current temp setup for this server.")
    @commands.cooldown(1, 5, BucketType.user)
    @commands.has_permissions(administrator=True)
    @is_not_blacklisted()
    @maintenance_check()
    async def get_temp_setup(self, ctx):
        bot_id = self.bot.user.id
        data = await unified_cache.get_temp_setup_data(ctx.guild.id, bot_id)
        if not data:
            return schedule_delete(await ctx.send(view=ts_design.no_setup()))

        text_channel = ctx.guild.get_channel(data["text_channel_id"])
        category = ctx.guild.get_channel(data["category_id"])
        tc_mention = text_channel.mention if text_channel else f"<#{data['text_channel_id']}>"
        cat_name = category.name if category else f"ID: {data['category_id']}"
        schedule_delete(await ctx.send(view=ts_design.current_setup(tc_mention, cat_name)))


async def setup(bot):
    await bot.add_cog(TempSetup(bot))
