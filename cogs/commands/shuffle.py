import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.dj_checker import dj_lockable
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.voice_connected import ensure_voice
from utils.embed_designs import shuffle as shuffle_design

load_dotenv()


class Shuffle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="shuffle", description="Shuffle the current queue.", aliases=['sh'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    @dj_lockable()
    async def shuffle(self, ctx: commands.Context):
        try:
            if not await ensure_voice(ctx):
                return

            player: LavaMusic = ctx.guild.voice_client
            if not player or not player.playing:
                await ctx.send(view=shuffle_design.not_playing(), ephemeral=True)
                return

            player.queue.shuffle()
            await ctx.send(view=shuffle_design.shuffled(), ephemeral=True)
        except Exception as e:
            await ctx.send(view=shuffle_design.error(str(e)), ephemeral=True)

async def setup(bot) -> None:
    await bot.add_cog(Shuffle(bot))
