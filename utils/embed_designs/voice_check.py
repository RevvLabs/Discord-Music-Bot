import discord
from utils.helper_function.embed_layout import build_basic_layout


def not_in_voice() -> discord.ui.LayoutView:
    return build_basic_layout(description="You need to be in a voice channel to use this command.")


def bot_not_connected() -> discord.ui.LayoutView:
    return build_basic_layout(description="I'm not connected to any voice channel.")


def different_voice() -> discord.ui.LayoutView:
    return build_basic_layout(description="You need to be in the same voice channel as me to use this command.")
