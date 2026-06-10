import discord
from discord.ext import commands
from discord.ext.commands import BucketType
import os
from dotenv import load_dotenv
from utils.helper_function.unified_cache_manager import unified_cache
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import maintenance as maint_design

load_dotenv()
BOT_OWNER_IDS = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]


def is_bot_owner():
    async def predicate(ctx: commands.Context):
        return ctx.author.id in BOT_OWNER_IDS
    return commands.check(predicate)


class MaintenanceControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="lock", description="Lock a command for maintenance. (Bot owner only)")
    @commands.cooldown(1, 2, BucketType.user)
    @is_bot_owner()
    async def lock(self, ctx: commands.Context, command_name: str, *, reason: str = ""):
        cmd = self.bot.get_command(command_name)
        if not cmd:
            return await ctx.send(view=maint_design.command_not_found(command_name), ephemeral=True)

        already = await unified_cache.is_command_locked(command_name)
        if already is not None:
            return await ctx.send(view=maint_design.already_locked(command_name), ephemeral=True)

        ok = await unified_cache.set_command_lock(command_name, True, reason)
        if ok:
            await ctx.send(view=maint_design.command_locked(command_name, reason), ephemeral=True)
        else:
            await ctx.send(view=maint_design.command_lock_failed(command_name), ephemeral=True)

    @commands.hybrid_command(name="unlock", description="Unlock a command from maintenance. (Bot owner only)")
    @commands.cooldown(1, 2, BucketType.user)
    @is_bot_owner()
    async def unlock(self, ctx: commands.Context, command_name: str):
        locked = await unified_cache.is_command_locked(command_name)
        if locked is None:
            return await ctx.send(view=maint_design.not_locked(command_name), ephemeral=True)

        ok = await unified_cache.set_command_lock(command_name, False)
        if ok:
            await ctx.send(view=maint_design.command_unlocked(command_name), ephemeral=True)
        else:
            await ctx.send(view=maint_design.command_unlock_failed(command_name), ephemeral=True)

    @commands.hybrid_command(name="locked", description="List all commands locked for maintenance. (Bot owner only)")
    @commands.cooldown(1, 3, BucketType.user)
    @is_bot_owner()
    async def locked(self, ctx: commands.Context):
        locks = await unified_cache.get_locked_commands()
        if not locks:
            return await ctx.send(view=maint_design.no_locked_commands(), ephemeral=True)

        lines = []
        for name, data in locks.items():
            reason = data.get("reason", "")
            lines.append(f"`{name}`" + (f" — {reason}" if reason else ""))

        await ctx.send(view=maint_design.locked_list(lines), ephemeral=True)


async def setup(bot):
    await bot.add_cog(MaintenanceControl(bot))
