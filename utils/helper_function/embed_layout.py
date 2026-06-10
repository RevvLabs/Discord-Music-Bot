import discord
from utils.helper_function.bot_config import EMBED_COLOR

def build_basic_layout(description: str, title: str = None, image_url: str = None, accent_color: discord.Color = None) -> discord.ui.LayoutView:
    color = accent_color if accent_color is not None else EMBED_COLOR
    view = discord.ui.LayoutView()

    content = description

    items = []
    if title:
        items.append(discord.ui.TextDisplay(content=f"## {title}"))

    items.append(discord.ui.TextDisplay(content=content))

    container = discord.ui.Container(*items, accent_color=color)

    if image_url:
        section = discord.ui.Section(
            title if title else "",
            content if not title else "",
            accessory=discord.ui.Thumbnail(image_url)
        )
        if not title:
            if items:
                items.pop()
        view.add_item(section)

    view.add_item(container)
    return view

def build_track_added_layout(track_title: str, artist: str, duration: str, image_url: str = None, title: str = "Now Playing", subtext: str = "Streaming now in voice channel") -> discord.ui.LayoutView:
    view = discord.ui.LayoutView()

    header = discord.ui.TextDisplay(content=f"## {title}")
    separator = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)

    display_title = track_title
    if len(display_title) > 25:
        display_title = display_title[:22] + "..."

    if image_url:
        section = discord.ui.Section(
            f"**{display_title}**",
            f"{artist}",
            f"{duration}\n{subtext}",
            accessory=discord.ui.Thumbnail(image_url)
        )
        content_item = section
    else:
        content_item = discord.ui.TextDisplay(content=f"**{display_title}**\n{artist}\n{duration}\n{subtext}")

    container = discord.ui.Container(header, separator, content_item, accent_color=EMBED_COLOR)

    view.add_item(container)
    return view
