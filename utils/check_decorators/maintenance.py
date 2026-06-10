import os
from discord.ext import commands
from utils.helper_function.unified_cache_manager import unified_cache

BOT_OWNER_IDS = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]


class MaintenanceModeActive(commands.CheckFailure):
    pass


class CommandUnderMaintenance(MaintenanceModeActive):
    def __init__(self, command_name: str, reason: str = ""):
        self.command_name = command_name
        self.reason = reason
        super().__init__(f"Command '{command_name}' is under maintenance")


def maintenance_check():
    async def predicate(ctx):
        is_blacklisted = await unified_cache.is_user_blacklisted(ctx.author.id)
        if is_blacklisted:
            return False

        if ctx.author.id in BOT_OWNER_IDS:
            return True

        # Per-command lock check
        if ctx.command:
            reason = await unified_cache.is_command_locked(ctx.command.name)
            if reason is not None:
                raise CommandUnderMaintenance(ctx.command.name, reason)

        # Global maintenance check
        if await unified_cache.is_maintenance_mode_enabled():
            raise MaintenanceModeActive()

        return True

    return commands.check(predicate)