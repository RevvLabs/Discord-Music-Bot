import discord
from utils.helper_function.embed_layout import build_basic_layout


def already_paused() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Pause\nThe track is already paused.")


def paused() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Paused\nThe track has been paused.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nFailed to pause the track: {msg}")


def general_error() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Error\nAn error occurred while pausing. Please try again.")
