import discord
from utils.helper_function.bot_config import EMBED_COLOR


def empty_history() -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🕓 Play History"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="No tracks have been played yet this session."),
        accent_color=EMBED_COLOR,
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def no_player() -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🕓 Play History"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="The bot is not connected to a voice channel."),
        accent_color=EMBED_COLOR,
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def history_list(tracks: list) -> discord.ui.LayoutView:
    items = [
        discord.ui.TextDisplay(content="## 🕓 Play History"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
    ]

    for i, track in enumerate(tracks, start=1):
        title = getattr(track, "title", "Unknown Title")
        uri = getattr(track, "uri", None)
        author = getattr(track, "author", "Unknown Artist")
        length_ms = getattr(track, "length", 0)
        minutes, seconds = divmod(length_ms // 1000, 60)
        duration = f"{minutes:02}m {seconds:02}s"

        title_str = title if len(title) <= 50 else title[:47] + "…"
        title_display = f"[{title_str}]({uri})" if uri else title_str

        label = "*(most recent)*" if i == 1 else ""
        line = f"**{i}.** {title_display} {label}\n> {author} · {duration}"
        items.append(discord.ui.TextDisplay(content=line))

        if i < len(tracks):
            items.append(discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small))

    items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    items.append(discord.ui.TextDisplay(content=f"*Showing last {len(tracks)} track(s) · most recent first*"))

    container = discord.ui.Container(*items, accent_color=EMBED_COLOR)
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view
