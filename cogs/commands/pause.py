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
from utils.embed_designs import pause as pause_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Pause(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="pause", description="Pauses the currently playing track.", aliases=['ps'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def pause(self, ctx: commands.Context):
        try:
            if not await ensure_voice(ctx):
                return

            try:
                player: LavaMusic = ctx.guild.voice_client
                if player.paused:
                    await ctx.send(view=pause_design.already_paused(), ephemeral=True)
                    return

                await player.pause(True)
                await ctx.send(view=pause_design.paused(), ephemeral=True)

                player.status = False
                await ctx.defer(ephemeral=True)
            except Exception as e:
                print(f"\033[91m[ERROR] Pause Player Error\033[0m: {e}")
                schedule_delete(await ctx.send(view=pause_design.error(str(e))))
        except Exception as e:
            print(f"\033[91m[ERROR] Pause Command Error\033[0m: {e}")
            schedule_delete(await ctx.send(view=pause_design.general_error()))

async def setup(bot) -> None:
    await bot.add_cog(Pause(bot))
