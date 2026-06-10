import discord
from utils.helper_function.embed_layout import build_basic_layout


def joined(channel_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Joined\n{channel_name} has been joined and is ready to play.")


def not_in_voice() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### Error\n**You need to be in a voice channel to use this command.**"
    )


def no_permissions(channel_mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Error\n**I don't have the necessary permissions to join or speak in {channel_mention}.**"
    )


def already_active(channel_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\n**I am already active in VC {channel_name}.**")


def already_here(channel_mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\n**I'm already in {channel_mention}.**")


def connect_error(channel_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nCould not join {channel_name}. Please try again.")
