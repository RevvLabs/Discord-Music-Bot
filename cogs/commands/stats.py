from datetime import datetime, timezone
import discord
from discord.ext import commands
import platform
import psutil
import time
from discord.ext.commands import BucketType
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
import asyncpg
import os

from utils.embed_designs import stats as stats_design
from utils.helper_function.auto_delete import schedule_delete

DATABASE_URL = os.getenv("DATABASE_URL")


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.start_time = time.time()

    @commands.hybrid_command(name="stats", description="Displays bot statistics.", aliases=['sts'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def stats(self, ctx: commands.Context):
        start_time = self.bot.start_time
        if isinstance(start_time, float):
            start_time = datetime.fromtimestamp(start_time, timezone.utc)
        uptime_duration = datetime.now(timezone.utc) - start_time
        days    = uptime_duration.days
        hours   = uptime_duration.seconds // 3600
        minutes = (uptime_duration.seconds % 3600) // 60
        seconds = uptime_duration.seconds % 60
        uptime_string = f"{days}d {hours}h {minutes}m {seconds}s"

        ws_latency = round(self.bot.latency * 1000, 2)

        t0 = time.perf_counter()
        await ctx.channel.typing()
        msg_latency = round((time.perf_counter() - t0) * 1000, 2)

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            db_t0 = time.perf_counter()
            await conn.execute("SELECT 1")
            db_latency = round((time.perf_counter() - db_t0) * 1000, 2)

            row = await conn.fetchrow(
                "SELECT SUM(count) AS total_count, SUM(minutes) AS total_minutes FROM user_counts"
            )
            global_songs_played      = int(row["total_count"])   if row and row["total_count"]   is not None else 0
            global_minutes_listening = int(row["total_minutes"]) if row and row["total_minutes"] is not None else 0
        finally:
            await conn.close()

        cpu_count    = psutil.cpu_count()
        system_name  = platform.system()
        system_info  = f"{cpu_count} cores · {system_name}"
        cpu_usage    = psutil.cpu_percent(interval=None)
        memory_usage = psutil.virtual_memory().used / (1024 ** 2)

        server_count = len(self.bot.guilds)
        user_count   = sum(guild.member_count for guild in self.bot.guilds)

        view = stats_design.stats_card(
            uptime_string=uptime_string,
            system_info=system_info,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            ws_latency=ws_latency,
            msg_latency=msg_latency,
            db_latency=db_latency,
            server_count=server_count,
            user_count=user_count,
            global_songs_played=global_songs_played,
            global_minutes_listening=global_minutes_listening,
            bot_avatar_url=self.bot.user.display_avatar.url,
        )
        schedule_delete(await ctx.send(view=view))


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))
