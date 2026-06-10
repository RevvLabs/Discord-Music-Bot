import discord
from utils.helper_function.embed_layout import build_basic_layout


def playing_previous(title: str) -> discord.ui.LayoutView:
    short = title[:50] + ("…" if len(title) > 50 else "")
    return build_basic_layout(description=f"### Previous\nNow playing the previous track: **{short}**")


def no_history() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Error\nThere is no previous track in history.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nFailed to play the previous track: {msg}")
