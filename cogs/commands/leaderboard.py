import discord
from discord.ext import commands
import asyncpg
import os
from dotenv import load_dotenv
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.setup_enforcer import enforce_setup
from discord.ext.commands import BucketType
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import leaderboard as lb_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="leaderboard", description="Displays the server leaderboard.", aliases=['lb', 'l'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def leaderboard(self, ctx):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return  
        guild_id = ctx.guild.id
        user_id = ctx.author.id

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch(
                """
                SELECT user_id, count, minutes
                FROM user_counts
                WHERE guild_id = $1
                ORDER BY count DESC, minutes DESC
                LIMIT 10
                """, guild_id)
            runner_data = await conn.fetchrow(
                """
                SELECT count, minutes
                FROM user_counts
                WHERE guild_id = $1 AND user_id = $2
                """, guild_id, user_id)
        finally:
            await conn.close()

        if not rows:
            schedule_delete(await ctx.send(view=lb_design.leaderboard_empty()))
            return

        leaderboard_content = ""
        rank = 1

        for db_user_id, count, minutes in rows:
            member = ctx.guild.get_member(db_user_id)
            if member:
                display_name = member.display_name
            else:
                try:
                    user_obj = await self.bot.fetch_user(db_user_id)
                    display_name = user_obj.display_name
                except (discord.NotFound, discord.HTTPException):
                    display_name = f"User {db_user_id}"
            leaderboard_content += f"**#{rank}** {display_name}\n└ **{count}** Songs Play • **{round(minutes, 2)}** Mins Listened\n\n"
            rank += 1

        if runner_data and runner_data[0] > 0 and user_id not in [row[0] for row in rows]:
            leaderboard_content += f"---\n**#{rank}** {ctx.author.display_name} (You)\n└ **{runner_data[0]}** Songs Play • **{round(runner_data[1], 2)}** Mins Listened"

        schedule_delete(await ctx.send(view=lb_design.leaderboard_card(ctx.guild.name, leaderboard_content)))

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
