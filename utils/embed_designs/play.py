import discord
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.embed_layout import build_basic_layout, build_track_added_layout


# ── Track / playlist added ────────────────────────────────────────────────────

def track_added(
    track_title: str,
    artist: str,
    duration: str,
    image_url: str | None = None,
    subtext: str = "Added to queue",
) -> discord.ui.LayoutView:
    return build_track_added_layout(
        track_title=track_title,
        artist=artist,
        duration=duration,
        image_url=image_url,
        title="Added to Queue",
        subtext=subtext,
    )


def playlist_added(name: str, count: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"Added the playlist **`{name}`** ({count} songs) to the queue."
    )


def play_next_added(
    track_title: str,
    artist: str,
    duration: str,
    image_url: str | None = None,
    subtext: str = "Will play next",
) -> discord.ui.LayoutView:
    return build_track_added_layout(
        track_title=track_title,
        artist=artist,
        duration=duration,
        image_url=image_url,
        title="Playing Next",
        subtext=subtext,
    )


def loading_playlist(name: str, count: int | None = None) -> discord.ui.LayoutView:
    if count:
        return build_basic_layout(
            description=f"Loading **`{name}`** ({count} songs) into the queue…"
        )
    return build_basic_layout(
        description="Please wait, loading the playlist… This may take a moment."
    )


def loading_spotify(name: str, sp_type: str, count: int) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"Loading Spotify {sp_type} **`{name}`** ({count} songs) into the queue…"
    )


# ── Voice / connection errors ────────────────────────────────────────────────

def not_in_voice() -> discord.ui.LayoutView:
    return build_basic_layout(description="You need to be in a voice channel to use this command.")


def different_voice() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="You need to be in the same voice channel as me to use this command."
    )


def connect_failed() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="Failed to connect to the voice channel. Please try again."
    )


def bot_joined(bot_name: str, channel_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"{bot_name} has joined **{channel_name}**")


# ── Queue / search errors ────────────────────────────────────────────────────

def queue_full(mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"{mention} — The queue is full. Please wait for tracks to finish."
    )


def no_results(mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"{mention} — Could not find any tracks with that query. "
                    "Please change the search engine and try again."
    )


def play_error() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="An error occurred while processing your request. Please try again."
    )


def track_error() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="An error occurred while processing the track. Please try again."
    )
