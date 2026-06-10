import discord
from utils.helper_function.embed_layout import build_basic_layout


def track_error(description: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Track Error", description=description)


def track_stuck(title: str, author: str, threshold: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        title="Track Stuck",
        description=(
            f"The track **{title}** got stuck and will be skipped.\n\n"
            f"**Threshold:** {threshold}ms\n\n"
            f"--- \nTrack by {author}"
        ),
    )


def websocket_closed(code: int, reason: str, by_remote: bool) -> discord.ui.LayoutView:
    return build_basic_layout(
        title="Connection Lost",
        description=(
            f"The connection to the voice server was lost.\n\n"
            f"**Code:** {code}\n"
            f"**Reason:** {reason}\n"
            f"**By Remote:** {by_remote}\n\n"
            f"--- \nAttempting to reconnect..."
        ),
    )


def node_disconnected() -> discord.ui.LayoutView:
    return build_basic_layout(
        title="Node Disconnected",
        description="The music node has been disconnected. The bot will attempt to reconnect automatically.\n\n--- \nPlease wait for reconnection...",
    )
