import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.voice_connected import ensure_voice
from utils.embed_designs import seek as seek_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Seek(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="seek", description="Seek to a specific time in the current track.", aliases=['sk'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def seek(self, ctx: commands.Context, time: str):
        try:
            if not await ensure_voice(ctx):
                return

            player: LavaMusic = ctx.guild.voice_client
            if not player or not player.playing:
                return schedule_delete(await ctx.send(view=seek_design.not_playing()))

            try:
                seconds = int(time)
            except ValueError:
                return schedule_delete(await ctx.send(view=seek_design.invalid_input()))

            await player.seek(seconds * 1000)
            schedule_delete(await ctx.send(view=seek_design.seeked(seconds)))

        except Exception as e:
            schedule_delete(await ctx.send(view=seek_design.error(str(e))))

async def setup(bot) -> None:
    await bot.add_cog(Seek(bot))
