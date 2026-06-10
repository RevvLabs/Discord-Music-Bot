import discord
from discord.ext import commands
import time
import aiohttp
import os
from dotenv import load_dotenv
load_dotenv()

def is_bot_owner(user_id):
    owners = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]
    return user_id in owners

from utils.embed_designs import blacklist as bl_design
from utils.helper_function.unified_cache_manager import unified_cache

BLACKLIST_WEBHOOK_URL = os.getenv('BLACKLIST_WEBHOOK_URL')
BOT_NAME = os.getenv('BOT_NAME')

class AutoBlacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.command_usage = {}
        self.cooldown_limit = 5
        self.cooldown_window = 4
        self.webhook_url = BLACKLIST_WEBHOOK_URL

    async def send_blacklist_log(self, user, guild, reason="spam"):
        if not self.webhook_url:
            return
        log_message = {
            "embeds": [{
                "title": "User Blacklisted",
                "description": f"**User** : {user.name} | {user.id}\n**Guild** : {guild.name if guild else 'DM'} | {guild.id if guild else '—'}\n**Bot** : {BOT_NAME}\n**Reason** : {reason}",
                "color": discord.Color.dark_embed().value
            }]
        }
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(self.webhook_url, json=log_message)
        except Exception as e:
            print(f"Error sending log to webhook: {e}")

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        user_id = ctx.author.id

        if await unified_cache.is_user_blacklisted(user_id):
            return

        now = time.time()
        if user_id not in self.command_usage:
            self.command_usage[user_id] = []
        self.command_usage[user_id].append(now)

        self.command_usage[user_id] = [
            timestamp for timestamp in self.command_usage[user_id]
            if now - timestamp <= self.cooldown_window
        ]

        if len(self.command_usage[user_id]) > self.cooldown_limit:
            await unified_cache.add_user_to_blacklist(user_id)
            await self.send_blacklist_log(ctx.author, ctx.guild, reason="command spam (auto)")
            await ctx.send(view=bl_design.user_blacklisted())

    @commands.hybrid_command(name="blacklist", description="Blacklist a user from using the bot.", aliases=['bl'])
    async def blacklist(self, ctx: commands.Context, user: discord.User):
        try:
            if not is_bot_owner(ctx.author.id):
                await ctx.send(view=bl_design.perm_denied())
                return

            if await unified_cache.is_user_blacklisted(user.id):
                await ctx.send(view=bl_design.already_blacklisted(user.mention))
                return

            ok = await unified_cache.add_user_to_blacklist(user.id)
            if not ok:
                await ctx.send(view=bl_design.error("database write failed"))
                return

            await self.send_blacklist_log(user, ctx.guild, reason=f"manual (by {ctx.author})")
            await ctx.send(view=bl_design.blacklisted(user.mention))
        except Exception as e:
            await ctx.send(view=bl_design.error(str(e)))

    @commands.hybrid_command(name="unblacklist", description="Unblacklist a user.", aliases=['ub'])
    async def unblacklist(self, ctx: commands.Context, user: discord.User):
        try:
            if not is_bot_owner(ctx.author.id):
                await ctx.send(view=bl_design.perm_denied())
                return

            if not await unified_cache.is_user_blacklisted(user.id):
                await ctx.send(view=bl_design.not_blacklisted(user.mention))
                return

            ok = await unified_cache.remove_user_from_blacklist(user.id)
            if not ok:
                await ctx.send(view=bl_design.error("database write failed"))
                return

            await ctx.send(view=bl_design.unblacklisted(user.mention))
        except Exception as e:
            await ctx.send(view=bl_design.error(str(e)))

async def setup(bot):
    await bot.add_cog(AutoBlacklist(bot))
