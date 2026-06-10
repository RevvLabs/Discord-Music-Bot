import discord
from utils.helper_function.bot_config import EMBED_COLOR


def lyrics_container(title: str, chunk: str, current_page: int, total_pages: int) -> discord.ui.Container:
    return discord.ui.Container(
        discord.ui.TextDisplay(content=f"## {title}"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"```\n{chunk}\n```"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"-# Page {current_page + 1}/{total_pages} • Source: lrclib"),
        accent_color=EMBED_COLOR,
    )


def lyrics_not_found(display_title: str) -> discord.ui.LayoutView:
    v = discord.ui.LayoutView()
    v.add_item(discord.ui.Container(
        discord.ui.TextDisplay(content=f"> No lyrics found for **{display_title}**."),
        accent_color=EMBED_COLOR,
    ))
    return v


def nothing_playing() -> discord.ui.LayoutView:
    v = discord.ui.LayoutView()
    v.add_item(discord.ui.Container(
        discord.ui.TextDisplay(content="> Nothing is playing. Provide a search query or start playing a song."),
        accent_color=EMBED_COLOR,
    ))
    return v
