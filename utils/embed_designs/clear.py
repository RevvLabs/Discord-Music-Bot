import discord
from utils.helper_function.embed_layout import build_basic_layout


def queue_cleared() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Cleared\nThe queue has been cleared.")


def queue_empty() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Empty\nNo queue found to clear.")
