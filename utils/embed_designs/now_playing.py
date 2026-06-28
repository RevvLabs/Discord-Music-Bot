import discord
from utils.helper_function.embed_layout import build_basic_layout


def not_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Not Playing\nNo track is currently playing.")


def now_playing_text(
    title: str,
    author: str,
    requested_by: str,
    elapsed: str,
    duration: str,
    progress_percent: float,
) -> discord.ui.LayoutView:
    """Text-only Now Playing, used when image uploads are blocked for the guild."""
    desc = (
        f"### Now Playing\n"
        f"**{title}**\n"
        f"{author}\n"
        f"--- \n"
        f"- Position: {elapsed} / {duration}  ({progress_percent:.0f}%)\n"
        f"- Requested by: {requested_by}\n\n"
        f"_Image card unavailable — file uploads are currently limited for this server._"
    )
    return build_basic_layout(description=desc)
