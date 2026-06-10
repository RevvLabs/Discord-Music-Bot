import discord
from discord.ext import commands
import voltricx
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.voice_connected import ensure_voice
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import loop as loop_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Loop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="loop", description="Cycle loop mode: off → track → queue → off.", aliases=['lp'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def loop(self, ctx: commands.Context):
        try:
            if not await enforce_setup(ctx, EMBED_COLOR):
                return
            if not await ensure_voice(ctx):
                return

            player: LavaMusic = ctx.guild.voice_client

            if not player or not player.current:
                await ctx.send(view=loop_design.not_playing(), ephemeral=True)
                return

            if player.queue.mode == voltricx.QueueMode.normal:
                player.queue.mode = voltricx.QueueMode.loop
                msg = "🔂 **Loop Track** enabled — repeating the current song."
            elif player.queue.mode == voltricx.QueueMode.loop:
                player.queue.mode = voltricx.QueueMode.loop_all
                msg = "🔁 **Loop Queue** enabled — repeating the entire queue."
            else:
                player.queue.mode = voltricx.QueueMode.normal
                msg = "➡️ **Loop off** — playing normally."

            schedule_delete(await ctx.send(view=loop_design.loop_updated(msg)))
        except Exception as e:
            await ctx.send(view=loop_design.error(str(e)), ephemeral=True)

    @commands.hybrid_command(name="loopqueue", description="Toggle queue loop mode on/off.", aliases=['lq', 'qloop'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def loopqueue(self, ctx: commands.Context):
        try:
            if not await enforce_setup(ctx, EMBED_COLOR):
                return
            if not await ensure_voice(ctx):
                return

            player: LavaMusic = ctx.guild.voice_client

            if not player or not player.current:
                await ctx.send(view=loop_design.not_playing_queue(), ephemeral=True)
                return

            if player.queue.mode == voltricx.QueueMode.loop_all:
                player.queue.mode = voltricx.QueueMode.normal
                msg = "➡️ **Loop Queue off** — playing normally."
            else:
                player.queue.mode = voltricx.QueueMode.loop_all
                msg = "🔁 **Loop Queue enabled** — repeating the entire queue."

            schedule_delete(await ctx.send(view=loop_design.loop_queue_updated(msg)))
        except Exception as e:
            await ctx.send(view=loop_design.error(str(e)), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Loop(bot))
