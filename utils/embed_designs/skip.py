import discord
from utils.helper_function.embed_layout import build_basic_layout


def skipped() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Skipped\nSuccessfully skipped the current track.")


def vote_started(timestamp: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Vote Skip Started!\nReact with ✅ to vote Yes and ❌ to vote No.\n\nVote ends in 30 seconds - <t:{timestamp}:R>"
    )


def vote_skipped() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Skipped\nSuccessfully skipped the current track based on the vote.")


def vote_failed() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Vote Failed\nVote skipped failed. Track will continue playing.")


def not_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Skip\nI'm not playing anything to skip.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nAn error occurred: {msg}")


def skip_error() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Error\nAn error occurred during the skip process. Please try again.")
