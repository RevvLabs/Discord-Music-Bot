import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.voice_connected import ensure_voice
from utils.embed_designs import replay as replay_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Replay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="replay", description="Plays the current song from the start.", aliases=['rp'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def replay(self, ctx: commands.Context):
        if not await ensure_voice(ctx):
            return

        try:
            player: LavaMusic = ctx.guild.voice_client
            if not player.playing:
                await ctx.send(view=replay_design.not_playing(), ephemeral=True)
                return

            track = player.current
            await player.play(track, replace=True)
            schedule_delete(await ctx.send(view=replay_design.replaying(track.title)))
        except Exception as e:
            schedule_delete(await ctx.send(view=replay_design.error(str(e))))

async def setup(bot) -> None:
    await bot.add_cog(Replay(bot))
