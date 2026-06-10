import discord
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.embed_layout import build_basic_layout


def save_picker_container() -> discord.ui.Container:
    """Header container for the save-favorite selection view."""
    return discord.ui.Container(
        discord.ui.TextDisplay(
            content="### Save Favorite\nWhat would you like to save to your favorites?"
        ),
        accent_color=EMBED_COLOR,
    )


def saved_current(title: str, uri: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=(
            f"### Added to Favorites\n[{title}]({uri})\n\n"
            "Use `[ fav, f ]` to view / play your favorites.\n"
            "Use `[ sf, savefav ]` to save more."
        )
    )


def saved_queue(count: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=(
            f"### Added to Favorites\nAdded **{count}** songs from the queue to your favorites!\n\n"
            "Use `[ fav, f ]` to play your favorites.\n"
            "Use `[ sf, savefav ]` to save more."
        )
    )


def no_track() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### No Track\nNo track is currently playing and the queue is empty."
    )


def no_track_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### No Track\nNo track is currently playing.")


def empty_queue() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Empty Queue\nNo songs are currently in the queue.")


def no_option_selected() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Cancelled\nNo option selected. Cancelled.")
