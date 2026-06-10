import discord
from utils.helper_function.embed_layout import build_basic_layout


def seeked(seconds: int) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Seeked\nJumped to **{seconds}** seconds in the track.")


def invalid_input() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Invalid Input\nPlease provide a valid number of seconds.")


def not_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Seek\nI'm not playing anything to seek.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nAn error occurred while seeking: {msg}")
