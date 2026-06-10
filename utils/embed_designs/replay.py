import discord
from utils.helper_function.embed_layout import build_basic_layout


def replaying(title: str) -> discord.ui.LayoutView:
    short = title[:50] + ("…" if len(title) > 50 else "")
    return build_basic_layout(description=f"### Replay\nReplaying the current track: **{short}**.")


def not_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Error\nNo song is currently playing.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nFailed to replay the track: {msg}")
