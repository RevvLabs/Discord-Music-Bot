import discord
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.embed_layout import build_basic_layout


# ── Search results picker ────────────────────────────────────────────────────

def search_results(
    query: str,
    result_count: int,
    user_mention: str,
    artwork_url: str | None,
    select_menu: discord.ui.Select,
) -> discord.ui.LayoutView:
    body = (
        f"> **Query** : `{query}`\n"
        f"> **Found** : `{result_count}` track(s)\n"
        f"> **User**  : {user_mention}\n"
        "Select a track from the menu below to add it to the queue."
    )

    if artwork_url:
        info_display = discord.ui.Section(
            "## Search Results",
            body,
            accessory=discord.ui.Thumbnail(artwork_url),
        )
        container_items = [info_display]
    else:
        container_items = [
            discord.ui.TextDisplay(content="## Search Results"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=body),
        ]

    select_row = discord.ui.ActionRow()
    select_row.add_item(select_menu)

    container = discord.ui.Container(*container_items, accent_color=EMBED_COLOR)
    view = discord.ui.LayoutView()
    view.add_item(container)
    view.add_item(discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small))
    view.add_item(select_row)
    return view


def track_selected(
    track_title: str,
    track_uri: str,
    author: str,
    duration: str,
    source: str,
    requester_name: str,
    is_playing_now: bool,
    artwork_url: str | None = None,
) -> discord.ui.LayoutView:
    header = "## Now Playing" if is_playing_now else "## Added to Queue"
    title_str = track_title[:60] + ("…" if len(track_title) > 60 else "")
    body = (
        f"> **Track**    : [{title_str}]({track_uri})\n"
        f"> **Artist**   : {author}\n"
        f"> **Duration** : {duration}\n"
        f"> **Source**   : {source}\n"
        f"> **Req by**   : {requester_name}"
    )

    if artwork_url:
        section = discord.ui.Section(header, body, accessory=discord.ui.Thumbnail(artwork_url))
        container = discord.ui.Container(section, accent_color=EMBED_COLOR)
    else:
        container = discord.ui.Container(
            discord.ui.TextDisplay(content=header),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=body),
            accent_color=EMBED_COLOR,
        )

    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


# ── Status / error messages ──────────────────────────────────────────────────

def searching(mention: str, query: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"{mention} — Searching for **`{query}`** across multiple sources…"
    )


def no_results(mention: str, query: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"{mention} — No results found for **`{query}`**. Try a different query."
    )


def not_authorized() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### Not Allowed\nOnly the person who ran `/search` can pick a track."
    )


def bot_disconnected() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Not Connected\nBot is no longer in a voice channel.")


def queue_full(mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Queue Full\n{mention} — The queue is full, please wait."
    )


def search_expired(mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"{mention} — Search expired. Run `/search` again to pick a track."
    )
