import discord
from utils.helper_function.embed_layout import build_basic_layout


def moved(title: str, from_pos: int, to_pos: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Moved\n**{title}** moved from position **{from_pos}** to **{to_pos}**."
    )


def same_position(position: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### No Change\nThe track is already at position **{position}**."
    )


def invalid_position(max_pos: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Error\nInvalid position. Please provide a number between **1** and **{max_pos}**."
    )


def empty_queue() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Error\nThe queue is currently empty.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nFailed to move the track: {msg}")
