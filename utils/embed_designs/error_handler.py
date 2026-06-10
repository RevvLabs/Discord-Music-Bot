import discord
from utils.helper_function.embed_layout import build_basic_layout

_BLACKLIST_GIF = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExam42b2c5ejFhcW80ZXhta3d0bjZjMHRzbnZrOW5xM3JtZzBydTUzMSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/4BXKwKrbZxVNm/giphy.gif"


def cooldown(seconds: float) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"This command is on cooldown. Try again in {seconds} seconds.")


def missing_permissions() -> discord.ui.LayoutView:
    return build_basic_layout(description="You do not have the required permissions to use this command.")


def missing_argument() -> discord.ui.LayoutView:
    return build_basic_layout(description="A required argument is missing. Please check the command usage.")


def command_maintenance(command_name: str, reason: str = "") -> discord.ui.LayoutView:
    reason_line = f"\n\n**Reason:** {reason}" if reason else ""
    return build_basic_layout(
        title="Command Under Maintenance",
        description=f"The `{command_name}` command is currently unavailable. Please come back later!{reason_line}",
    )


def maintenance_mode() -> discord.ui.LayoutView:
    return build_basic_layout(
        title="Maintenance Mode",
        description="The bot is currently under maintenance and will be back soon.",
    )


def blacklisted() -> discord.ui.LayoutView:
    return build_basic_layout(
        title="Access Denied",
        description="You have been blacklisted from using this bot.",
        image_url=_BLACKLIST_GIF,
    )


def dj_role_required(role_name: str | None = None) -> discord.ui.LayoutView:
    target = f"the **{role_name}**" if role_name else "the **DJ**"
    return build_basic_layout(
        title="DJ Only",
        description=f"You need {target} role to use this command.",
    )


def unexpected_error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Unexpected Error", description=f"```{msg}```")


def critical_error() -> discord.ui.LayoutView:
    return build_basic_layout(
        title="Critical Error",
        description="An unexpected error occurred while handling another error.",
    )
