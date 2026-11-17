import discord
from utils.helper_function.embed_layout import build_basic_layout


def shuffled(up_next: list[str] | None = None) -> discord.ui.LayoutView:
    description = "### 🔀 Shuffled\nThe queue has been shuffled."
    if up_next:
        lines = "\n".join(f"`{i}.` {title[:80]}" for i, title in enumerate(up_next, 1))
        description += f"\n\n**Up next:**\n{lines}"
    return build_basic_layout(description=description)


def up_next_titles(queue, count: int = 3) -> list[str]:
    """First few queued track titles, used to show the new order after a shuffle."""
    return [getattr(track, "title", None) or "Unknown" for track in list(queue)[:count]]


def not_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Shuffle\nI'm not playing anything to shuffle.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"### Error\nAn error occurred: {msg}")
