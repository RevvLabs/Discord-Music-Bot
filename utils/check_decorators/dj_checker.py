import os
from discord.ext import commands
from utils.helper_function.unified_cache_manager import unified_cache

BOT_OWNER_IDS = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]

# Commands that are DJ-locked by default. Guild admins can override these via /djlock and /djunlock.
DEFAULT_DJ_LOCKED_COMMANDS = frozenset({
    "shuffle", "move", "engine", "dedicate",
    "bassboost", "nightcore", "vaporwave", "karaoke", "8d", "chipmunk", "deepvoice", "reset",
})


class NotDJ(commands.CheckFailure):
    """Raised when a DJ-locked command is used by someone without the DJ role."""
    def __init__(self, role_id: "int | None" = None):
        self.role_id = role_id
        super().__init__("User lacks the DJ role")


async def dj_check_member(member, guild) -> "tuple[bool, int | None]":
    """
    Core DJ-lock logic. Returns (allowed, dj_role_id).

    Bypass rules:
      • If NO DJ role is set for the guild → allowed (lock inactive).
      • Bot owners always allowed.
      • Server admins / managers (administrator or manage_guild) allowed.
      • Members with the DJ role allowed.
      • Everyone else → not allowed.
    """
    if guild is None:
        return True, None

    dj_role_id = await unified_cache.get_dj_role(guild.id)
    if not dj_role_id:
        return True, None

    if member.id in BOT_OWNER_IDS:
        return True, dj_role_id

    perms = getattr(member, "guild_permissions", None)
    if perms and (perms.administrator or perms.manage_guild):
        return True, dj_role_id

    if any(r.id == dj_role_id for r in getattr(member, "roles", [])):
        return True, dj_role_id

    return False, dj_role_id


async def member_is_dj(member, guild) -> bool:
    """Convenience boolean wrapper around dj_check_member for use in UI callbacks."""
    allowed, _ = await dj_check_member(member, guild)
    return allowed


async def dj_predicate(ctx: commands.Context) -> bool:
    """Shared DJ-lock check for cog_check / the dj_only() decorator. Raises NotDJ if denied."""
    allowed, role_id = await dj_check_member(ctx.author, ctx.guild)
    if not allowed:
        raise NotDJ(role_id)
    return True


async def dynamic_dj_predicate(ctx: commands.Context) -> bool:
    """
    DJ check that respects per-guild command lock overrides.
    Falls back to DEFAULT_DJ_LOCKED_COMMANDS when no override exists for the guild.
    """
    if ctx.guild is None:
        return True

    command_name = ctx.command.name if ctx.command else ""
    overrides = await unified_cache.get_command_dj_overrides(ctx.guild.id)

    if command_name in overrides:
        locked = overrides[command_name]
    else:
        locked = command_name in DEFAULT_DJ_LOCKED_COMMANDS

    if not locked:
        return True

    allowed, role_id = await dj_check_member(ctx.author, ctx.guild)
    if not allowed:
        raise NotDJ(role_id)
    return True


def dj_only():
    """Restrict a command to members holding the guild's configured DJ role (always-on check)."""
    return commands.check(dj_predicate)


def dj_lockable():
    """
    Restrict a command to DJ role only if it's locked for this guild.
    Guild admins can toggle locking via /djlock and /djunlock.
    Falls back to DEFAULT_DJ_LOCKED_COMMANDS when no per-guild override exists.
    """
    return commands.check(dynamic_dj_predicate)
