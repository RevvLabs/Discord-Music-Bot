import discord
from utils.helper_function.embed_layout import build_basic_layout


def loop_updated(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Loop\n{msg}")


def loop_queue_updated(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Loop Queue\n{msg}")


def not_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Loop\nI'm not playing anything to loop.")


def not_playing_queue() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Loop Queue\nI'm not playing anything to loop.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nAn error occurred: {msg}")
