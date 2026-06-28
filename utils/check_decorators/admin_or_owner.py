"""
admin_or_owner check
=====================
Gate a command behind a guild permission OR bot ownership. Bot owners listed in
the BOT_OWNER_IDS env var bypass the permission requirement entirely, so they can
run setup-style commands (/setup, /temp-setup, /dj, etc.) in any guild.

Usage:
    @admin_or_owner()                    # administrator OR bot owner
    @admin_or_owner(manage_guild=True)   # manage_guild (or admin) OR bot owner
"""
import os
from discord.ext import commands

_BOT_OWNER_IDS = {int(x) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip().isdigit()}


def admin_or_owner(*, manage_guild: bool = False):
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id in _BOT_OWNER_IDS:
            return True
        perms = getattr(ctx.author, "guild_permissions", None)
        if perms and (perms.administrator or (manage_guild and perms.manage_guild)):
            return True
        # Raise the same error has_permissions would, so the existing error
        # handler shows the usual "missing permission" message.
        raise commands.MissingPermissions(["manage_guild" if manage_guild else "administrator"])
    return commands.check(predicate)
