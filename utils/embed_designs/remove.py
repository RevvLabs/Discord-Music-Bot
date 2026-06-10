import discord
from utils.helper_function.embed_layout import build_basic_layout


def removed(title: str, position: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Removed\nRemoved track **{title}** at position {position} from the queue."
    )


def invalid_position(max_pos: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Error\nInvalid position. Please provide a number between 1 and {max_pos}."
    )


def empty_queue() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Error\nThe queue is currently empty.")


def not_found() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Error\nThe specified track was not found in the queue.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nFailed to remove the track: {msg}")
