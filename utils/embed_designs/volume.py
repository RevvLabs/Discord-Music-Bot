import discord
from utils.helper_function.embed_layout import build_basic_layout


def volume_set(vol: int) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Volume\nVolume is now set to: **{vol}**%")


def out_of_range() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Invalid Input\nVolume value should be in the range of `1-100`.")


def not_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Volume\nI'm not playing anything to adjust volume.")


def not_in_voice() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Voice\nYou need to join a voice channel first.")
