import discord
from utils.helper_function.bot_config import EMBED_COLOR


def autoplay_picker_container(playlists: list) -> discord.ui.Container:
    """Returns the header container for the autoplay playlist picker view."""
    lines = ["## 🎵 Autoplay Playlists", "Pick a playlist to start playing instantly.\n"]
    for pl in playlists:
        lines.append(f"**{pl['name']}** — {pl['platform']} · {pl['track_count']} tracks")
    return discord.ui.Container(
        discord.ui.TextDisplay(content="\n".join(lines)),
        accent_color=EMBED_COLOR,
    )


def autoplay_stopped() -> discord.ui.LayoutView:
    from utils.helper_function.embed_layout import build_basic_layout
    return build_basic_layout(
        description="⏹ Autoplay stopped. The current song will finish and "
                    "no more tracks will be added automatically."
    )


def autoplay_no_playlists() -> discord.ui.LayoutView:
    from utils.helper_function.embed_layout import build_basic_layout
    return build_basic_layout(
        title="Autoplay",
        description="No playlists have been added yet.\n"
                    "Ask a bot admin to add playlists via `!autoplaymanager`."
    )
