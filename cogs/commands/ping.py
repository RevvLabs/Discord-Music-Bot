import asyncio
import discord
import time
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.embed_designs import ping as ping_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Displays the bot, API, and database latencies.")
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def ping(self, ctx):
        start_time = time.monotonic()
        ws_latency = round(self.bot.latency * 1000, 2)

        if ctx.interaction:
            await ctx.interaction.response.send_message("Pinging...")
            end_time = time.monotonic()
            latency = round((end_time - start_time) * 1000, 2)
            await ctx.interaction.edit_original_response(
                content=None,
                view=ping_design.pong(latency, ws_latency),
            )
            # delete_original_response() avoids the InteractionCallbackResponse.delete()
            # AttributeError that occurs when using original_response() in newer discord.py.
            async def _delete_slash():
                await asyncio.sleep(60)
                try:
                    await ctx.interaction.delete_original_response()
                except Exception:
                    pass

            asyncio.create_task(_delete_slash())
        else:
            message = await ctx.send("Pinging...")
            end_time = time.monotonic()
            latency = round((end_time - start_time) * 1000, 2)
            await message.edit(content=None, view=ping_design.pong(latency, ws_latency))
            schedule_delete(message)

async def setup(bot):
    await bot.add_cog(Ping(bot))
