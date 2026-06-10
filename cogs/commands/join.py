import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import join as join_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Join(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="join", description="Join the voice channel that the user is in.", aliases=["j"])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def join(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not ctx.author.voice or not ctx.author.voice.channel:
            return schedule_delete(await ctx.send(view=join_design.not_in_voice()))

        channel = ctx.author.voice.channel
        player = ctx.guild.voice_client

        permissions = channel.permissions_for(ctx.guild.me)
        if not permissions.connect or not permissions.speak:
            return schedule_delete(await ctx.send(view=join_design.no_permissions(channel.mention)))

        if player and player.channel != channel:
            return schedule_delete(await ctx.send(view=join_design.already_active(player.channel.name)))

        if player and player.channel == channel:
            return schedule_delete(await ctx.send(view=join_design.already_here(channel.mention)))

        try:
            await channel.connect(cls=LavaMusic)
            schedule_delete(await ctx.send(view=join_design.joined(f"{self.bot.user.name} has joined {channel.name}")))
        except discord.errors.ClientException:
            schedule_delete(await ctx.send(view=join_design.connect_error(channel.name)))

async def setup(bot) -> None:
    await bot.add_cog(Join(bot))
