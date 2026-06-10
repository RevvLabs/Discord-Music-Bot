import discord
from utils.helper_function.embed_layout import build_basic_layout


def shuffled() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Shuffled\nThe queue has been shuffled.")


def not_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Shuffle\nI'm not playing anything to shuffle.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nAn error occurred: {msg}")
