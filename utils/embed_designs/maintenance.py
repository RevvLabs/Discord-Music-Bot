import discord
from utils.helper_function.embed_layout import build_basic_layout


def command_not_found(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Command Not Found", description=f"No command named `{name}` exists.")


def already_locked(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Already Locked", description=f"`{name}` is already locked.")


def command_locked(name: str, reason: str = "") -> discord.ui.LayoutView:
    reason_line = f"\n**Reason:** {reason}" if reason else ""
    return build_basic_layout(title="Command Locked", description=f"`{name}` is now under maintenance.{reason_line}")


def command_lock_failed(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Failed", description=f"Could not lock `{name}`. Check logs.")


def not_locked(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Not Locked", description=f"`{name}` is not currently locked.")


def command_unlocked(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Command Unlocked", description=f"`{name}` is now available again.")


def command_unlock_failed(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Failed", description=f"Could not unlock `{name}`. Check logs.")


def no_locked_commands() -> discord.ui.LayoutView:
    return build_basic_layout(title="No Locked Commands", description="All commands are currently available.")


def locked_list(lines: list) -> discord.ui.LayoutView:
    return build_basic_layout(
        title=f"Locked Commands ({len(lines)})",
        description="\n".join(lines),
    )
