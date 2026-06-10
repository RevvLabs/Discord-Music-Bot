import discord
from utils.helper_function.embed_layout import build_basic_layout


def disconnected() -> discord.ui.LayoutView:
    return build_basic_layout(description="Disconnected")


def not_connected() -> discord.ui.LayoutView:
    return build_basic_layout(description="I'm not connected to any voice channel.")
