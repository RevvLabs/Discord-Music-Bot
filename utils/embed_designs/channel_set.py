import discord
from utils.helper_function.embed_layout import build_basic_layout


def setup_done(text_mention: str, voice_mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Bot Setup Completed\nText channel set to : **{text_mention}**\nVoice channel set to : **{voice_mention}**."
    )


def setup_cleared() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### Setup Cleared\nThe Text and voice channel setup has been cleared for this server."
    )


def current_setup(text_mention: str, voice_mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Current Setup\nText channel: **{text_mention}**\nVoice channel: **{voice_mention}**"
    )


def no_setup() -> discord.ui.LayoutView:
    return build_basic_layout(description="### No Setup Found\nNo channels set for this server.")
