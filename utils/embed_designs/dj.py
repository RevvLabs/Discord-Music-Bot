import discord
from utils.helper_function.embed_layout import build_basic_layout


def dj_role_set(role_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### DJ Role Set\n**{role_name}** can now skip tracks instantly — no vote required."
    )


def dj_role_cleared() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### DJ Role Removed\nThe DJ role has been cleared. Everyone now uses the vote-to-skip flow."
    )


def dj_role_status(role_name: str | None) -> discord.ui.LayoutView:
    if role_name:
        body = f"The current DJ role is **{role_name}**.\nMembers with this role bypass vote-to-skip."
    else:
        body = "No DJ role is set. Everyone uses the vote-to-skip flow."
    return build_basic_layout(description=f"### DJ Role\n{body}")


def no_permission() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### Permission Denied\nYou need the **Manage Server** permission to configure the DJ role."
    )


def save_failed() -> discord.ui.LayoutView:
    return build_basic_layout(description="Failed to update the DJ role. Please try again.")


def command_locked(command_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Command Locked\n`/{command_name}` is now DJ-only for this server."
    )


def command_unlocked(command_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Command Unlocked\n`/{command_name}` is now available to everyone in this server."
    )


def command_already_locked(command_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Already Locked\n`/{command_name}` is already DJ-only in this server."
    )


def command_already_unlocked(command_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Already Unlocked\n`/{command_name}` is already available to everyone in this server."
    )


def no_dj_role_warning(command_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=(
            f"### Command Locked\n`/{command_name}` has been marked as DJ-only, but **no DJ role is set** for this server.\n"
            "Use `/djset` to assign a DJ role — until then the lock has no effect."
        )
    )


def lock_status(locked: list[str], unlocked_overrides: list[str]) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView()

    locked_text = "\n".join(f"- `/{c}`" for c in sorted(locked)) if locked else "*None*"
    unlock_text = "\n".join(f"- `/{c}`" for c in sorted(unlocked_overrides)) if unlocked_overrides else "*None*"

    container = discord.ui.Container(
        discord.ui.TextDisplay(content="### DJ Command Lock Status"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"**Locked (DJ only)**\n{locked_text}"),
        discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"**Unlocked (overridden from default)**\n{unlock_text}"),
        accent_color=discord.Color.from_rgb(88, 101, 242),
    )
    view.add_item(container)
    return view
