import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.voice_connected import ensure_voice
from utils.embed_designs import volume as volume_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class volume(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="volume", description="Adjusts the volume of the music player.", aliases=["v", "vol"])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def volume(self, ctx: commands.Context, volume: int):
        if not await ensure_voice(ctx):
            return

        player: LavaMusic = ctx.guild.voice_client
        if not player.playing:
            return schedule_delete(await ctx.send(view=volume_design.not_playing()))
        if volume < 1 or volume > 100:
            return schedule_delete(await ctx.send(view=volume_design.out_of_range()))
        await player.set_volume(volume)
        schedule_delete(await ctx.send(view=volume_design.volume_set(volume)))

        if hasattr(player, 'interaction_view'):
            pass  # UI update skipped as card no longer shows volume status

    async def ensure_voice(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            schedule_delete(await ctx.send(view=volume_design.not_in_voice()))
            return False
        return True

async def setup(bot) -> None:
    await bot.add_cog(volume(bot))
