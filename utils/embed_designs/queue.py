import discord
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.embed_layout import build_basic_layout


def empty_queue() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Empty\nThe queue is currently empty.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nFailed to display the queue: {msg}")


def queue_page_container(page: int, total_pages: int, items: list) -> discord.ui.Container:
    """Container for one page of queue entries. `items` is a list of discord.ui components."""
    header = discord.ui.TextDisplay(content=f"## Songs In Queue (Page {page}/{total_pages})")
    return discord.ui.Container(*([header] + items), accent_color=EMBED_COLOR)
