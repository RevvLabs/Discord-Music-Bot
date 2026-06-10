import discord
from utils.helper_function.embed_layout import build_basic_layout


def not_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Not Playing\nNo track is currently playing.")
