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
from utils.embed_designs import remove as remove_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Remove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="remove",
        description="Removes a song from the queue by its position.",
        aliases=["rm"],
    )
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def remove(self, ctx: commands.Context, position: int):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not await ensure_voice(ctx):
            return

        try:
            player: LavaMusic = ctx.guild.voice_client
            if not player or not player.queue:
                await ctx.send(view=remove_design.empty_queue(), ephemeral=True)
                return

            if position < 1 or position > len(player.queue):
                await ctx.send(view=remove_design.invalid_position(len(player.queue)), ephemeral=True)
                return

            track_to_remove = player.queue[position - 1]
            player.queue.remove(track_to_remove, count=1)
            schedule_delete(await ctx.send(view=remove_design.removed(track_to_remove.title, position)))
        except ValueError:
            schedule_delete(await ctx.send(view=remove_design.not_found()))
        except Exception as e:
            schedule_delete(await ctx.send(view=remove_design.error(str(e))))

async def setup(bot) -> None:
    await bot.add_cog(Remove(bot))
