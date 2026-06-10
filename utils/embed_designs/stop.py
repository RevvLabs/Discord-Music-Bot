import discord
from utils.helper_function.bot_config import EMBED_COLOR


def stop_card(
    track_title: str | None,
    thumbnail_url: str | None,
    stopped_by_mention: str,
) -> discord.ui.LayoutView:
    if track_title:
        title_short = track_title[:60] + ("…" if len(track_title) > 60 else "")
        body = f"**{title_short}**\nStopped by {stopped_by_mention}"
        items = [discord.ui.TextDisplay(content="## 🛑 Stopped")]
        items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        if thumbnail_url:
            items.append(discord.ui.Section(body, accessory=discord.ui.Thumbnail(thumbnail_url)))
        else:
            items.append(discord.ui.TextDisplay(content=body))
    else:
        items = [discord.ui.TextDisplay(
            content=f"## 🛑 Stopped\nPlayer stopped by {stopped_by_mention}"
        )]

    container = discord.ui.Container(*items, accent_color=EMBED_COLOR)
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view
