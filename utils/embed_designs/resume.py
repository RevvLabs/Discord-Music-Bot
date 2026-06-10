import discord
from utils.helper_function.embed_layout import build_basic_layout


def already_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Resume\nThe track is already playing.")


def resumed() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Resumed\nThe track has been resumed.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nFailed to resume the track: {msg}")
