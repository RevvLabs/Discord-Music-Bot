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
from utils.embed_designs import resume as resume_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Resume(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="resume", description="Resumes the currently paused track.", aliases=['res'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def resume(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not await ensure_voice(ctx):
            return

        try:
            player: LavaMusic = ctx.guild.voice_client
            if not player.paused:
                await ctx.send(view=resume_design.already_playing(), ephemeral=True)
                return

            await player.pause(False)
            await ctx.send(view=resume_design.resumed(), ephemeral=True)

            player.status = True
            await ctx.defer(ephemeral=True)
        except Exception as e:
            schedule_delete(await ctx.send(view=resume_design.error(str(e))))

async def setup(bot) -> None:
    await bot.add_cog(Resume(bot))
