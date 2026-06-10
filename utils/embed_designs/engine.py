import discord
from utils.helper_function.embed_layout import build_basic_layout


def engine_picker() -> discord.ui.LayoutView:
    """Base view for engine selection. Caller should add ActionRows with engine buttons."""
    return build_basic_layout(
        description="### Select Your Search Engine\nPlease choose your preferred search engine by clicking one of the buttons below. Choose **Auto** to use the default prioritized search sequence."
    )


def engine_reset() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### Engine Reset\nYou have reset your search engine to **Auto**. The bot will now use the default prioritized search sequence."
    )


def engine_selected(emoji: str, name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Engine Selected\nYou have selected {emoji} **{name}** as your search engine.")


def not_authorized() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Error\nYou are not allowed to interact with these buttons.")
