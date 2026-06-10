import discord
from utils.helper_function.embed_layout import build_basic_layout


def controls_updated(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Controls Updated\n{msg}")
