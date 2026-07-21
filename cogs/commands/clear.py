import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.voice_connected import ensure_voice
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import clear as clear_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="clearqueue", description="Clean the current queue.", aliases=["cq", "clear"])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def clearQueue(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not await ensure_voice(ctx):
            return

        player: LavaMusic = ctx.guild.voice_client

        from cogs.commands.playlist import stop_playlist_session, has_playlist_session
        has_pending = has_playlist_session(ctx.guild.id)

        if len(player.queue) > 0 or has_pending:
            player.queue.clear()
            # Kill the playlist trickle-feed too, else it silently refills the
            # queue right after the user asked to clear it.
            stop_playlist_session(ctx.guild.id)
            schedule_delete(await ctx.send(view=clear_design.queue_cleared()))
        else:
            schedule_delete(await ctx.send(view=clear_design.queue_empty()))

async def setup(bot) -> None:
    await bot.add_cog(Clear(bot))
