import discord
from utils.helper_function.embed_layout import build_basic_layout


def wrong_channel(channel_mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        title="Wrong Channel!",
        description=f"Please use commands in {channel_mention}"
    )


def wrong_voice(channel_mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=(
            f"**You need to be in the voice channel to use this command.**\n\n"
            f"Please join {channel_mention} and try again."
        )
    )
