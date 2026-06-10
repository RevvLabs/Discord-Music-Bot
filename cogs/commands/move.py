import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.dj_checker import dj_lockable
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.voice_connected import ensure_voice
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import move as move_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Move(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="move",
        description="Move a queued song from one position to another.",
        aliases=["mv"],
    )
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    @dj_lockable()
    async def move(self, ctx: commands.Context, from_position: int, to_position: int):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not await ensure_voice(ctx):
            return

        try:
            player: LavaMusic = ctx.guild.voice_client
            if not player or not player.queue or len(player.queue) == 0:
                await ctx.send(view=move_design.empty_queue(), ephemeral=True)
                return

            size = len(player.queue)
            if from_position < 1 or from_position > size:
                await ctx.send(view=move_design.invalid_position(size), ephemeral=True)
                return
            if to_position < 1 or to_position > size:
                await ctx.send(view=move_design.invalid_position(size), ephemeral=True)
                return

            if from_position == to_position:
                await ctx.send(view=move_design.same_position(to_position), ephemeral=True)
                return

            track = player.queue[from_position - 1]
            player.queue.remove(track, count=1)
            # After removal the queue shrank by one; insert at the target index.
            # list.insert clamps out-of-range indices, so the last slot works too.
            player.queue.put_at(to_position - 1, track)

            schedule_delete(await ctx.send(view=move_design.moved(track.title, from_position, to_position)))
        except ValueError:
            schedule_delete(await ctx.send(view=move_design.error("track not found in the queue")))
        except Exception as e:
            schedule_delete(await ctx.send(view=move_design.error(str(e))))


async def setup(bot) -> None:
    await bot.add_cog(Move(bot))
