import discord
from discord.ext import commands
from discord.ext.commands import BucketType

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.auto_delete import schedule_delete
from utils.embed_designs import history as history_design


class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="history",
        description="Show the last 10 tracks played this session.",
        aliases=["hist", "recent"],
    )
    @commands.cooldown(1, 5, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def history(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return

        player: LavaMusic = ctx.guild.voice_client
        if not player:
            schedule_delete(await ctx.send(view=history_design.no_player()))
            return

        raw_history = list(getattr(player.queue, "history", []))
        if not raw_history:
            schedule_delete(await ctx.send(view=history_design.empty_history()))
            return

        # Most recent first, cap at 10
        tracks = list(reversed(raw_history))[:10]
        schedule_delete(await ctx.send(view=history_design.history_list(tracks)))


async def setup(bot):
    await bot.add_cog(History(bot))
