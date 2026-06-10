import discord
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.embed_layout import build_basic_layout


def favorites_page_container(title: str, content: str) -> discord.ui.Container:
    """Main paginated list container — title is e.g. '❤️ Favorites (page 1/3)'."""
    return discord.ui.Container(
        discord.ui.TextDisplay(content=f"## {title}"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=content),
        accent_color=EMBED_COLOR,
    )


def not_authorized() -> discord.ui.LayoutView:
    return build_basic_layout(description="You cannot control this pagination.")


def favorites_loading() -> discord.ui.LayoutView:
    return build_basic_layout(description="Loading selected songs, please wait…")


def favorites_added(count: int) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"Added **{count}** selected favorite track(s) to the queue!")


def no_valid_favorites() -> discord.ui.LayoutView:
    return build_basic_layout(description="No valid favorite songs could be added.")


def favorites_closed() -> discord.ui.LayoutView:
    return build_basic_layout(description="Favorite list closed.")


def favorites_timeout() -> discord.ui.LayoutView:
    return build_basic_layout(description="Favorite list timed out.")


def currently_loading() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="Your favorites are currently being loaded. Please wait until the process finishes."
    )


def no_favorites_saved() -> discord.ui.LayoutView:
    return build_basic_layout(description="You have no favorite songs saved.")


def no_valid_tracks_play_all() -> discord.ui.LayoutView:
    return build_basic_layout(description="No valid favorite songs could be added to the queue.")


def batch_queued(start: int, end: int, count: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"Added **{count}** track(s) (#{start}–#{end}) to the queue!"
    )
