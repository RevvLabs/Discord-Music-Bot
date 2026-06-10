import discord
from utils.helper_function.embed_layout import build_basic_layout
from utils.colours.embed_text_colours import wrap_red, wrap_yellow, wrap_green


def permission_denied() -> discord.ui.LayoutView:
    return build_basic_layout(description=wrap_red("You do not have permission to use this command."))


def cancelled() -> discord.ui.LayoutView:
    return build_basic_layout(description="Command cancelled.")


def no_confirmation() -> discord.ui.LayoutView:
    return build_basic_layout(description="No confirmation received. Command cancelled.")


def timed_out() -> discord.ui.LayoutView:
    return build_basic_layout(description="Timed out. Command cancelled.")


def no_nodes() -> discord.ui.LayoutView:
    return build_basic_layout(description="No Lavalink nodes are connected.")


def node_error(idx: int, msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"Node {idx}: Failed to fetch stats: {msg}")


def engine_updated(changes: list) -> discord.ui.LayoutView:
    return build_basic_layout(title="Engine Status Updated", description="\n".join(changes))


def cache_stats(l1: int, l2: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        title="HyperCache Statistics",
        description=f"**L1 (Queries):** `{l1}`\n**L2 (Tracks):** `{l2}`",
    )


def cache_exported(file_path: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=wrap_green(f"Cache exported successfully to `{file_path}`"))


def force_fix_warning() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="**WARNING**: This will force disconnect all voice connections!\n\nClick the button below to confirm with a modal."
    )


def force_fix_success() -> discord.ui.LayoutView:
    return build_basic_layout(description=wrap_yellow("Successfully force fixed all voice connections."))


def force_fix_error() -> discord.ui.LayoutView:
    return build_basic_layout(description="An error occurred while force fixing the connections. Check console.")


def debug_toggle(enabled: bool, node_count: int) -> discord.ui.LayoutView:
    status_label = wrap_green("ENABLED") if enabled else wrap_red("DISABLED")
    return build_basic_layout(
        title="Voltricx Debug Logging",
        description=(
            f"Debug logging is now **{status_label}**\n\n"
            f"Connected nodes: `{node_count}`\n"
            f"Log level: `{'DEBUG' if enabled else 'OFF'}`\n\n"
            f"{'All internal voltricx operations will now be printed to console.' if enabled else 'Logging has been silenced. No performance overhead.'}\n\n"
            f"--- \nUse /debugbot again to toggle back."
        ),
    )


def autoplay_mgr_permission_denied() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### Permission Denied\nYou need to be a bot owner or AUTOPLAY_CONTROLLERS member to use this command."
    )


def visualiser_panel(description: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=description)
