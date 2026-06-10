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
from utils.embed_designs import previous as prev_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Previous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="previous", description="Plays the previous track.", aliases=["prev"])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def previous(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not await ensure_voice(ctx):
            return

        player: LavaMusic = ctx.guild.voice_client

        if len(player.queue.history) < 2:
            schedule_delete(await ctx.send(view=prev_design.no_history()))
            return

        try:
            _current = player.queue.history.pop()
            previous_track = player.queue.history.pop()
            player.queue.put_at_front(previous_track)
            await player.skip(force=True)
            schedule_delete(await ctx.send(view=prev_design.playing_previous(previous_track.title)))
        except Exception as e:
            schedule_delete(await ctx.send(view=prev_design.error(str(e))))

async def setup(bot) -> None:
    await bot.add_cog(Previous(bot))
