import discord
from utils.helper_function.embed_layout import build_basic_layout


def filter_enabled(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Filter Enabled\nEnabled the **{name}** filter.")


def filter_disabled(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Filter Disabled\nDisabled the **{name}** filter.")


def filters_reset() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Filters Reset\nAll filters have been reset.")


def not_connected() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Error\nI'm not connected to any voice channel.")


def invalid_filter(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nInvalid filter type: **{name}**.")
