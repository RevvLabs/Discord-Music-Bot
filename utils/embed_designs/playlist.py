import discord
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.embed_layout import build_basic_layout


# ── Success messages ─────────────────────────────────────────────────────────

def song_added(title: str, author: str, playlist_name: str) -> discord.ui.LayoutView:
    label = f"**{title}**" + (f" — {author}" if author else "")
    return build_basic_layout(description=f"Added {label} to **{playlist_name}**.")


def songs_removed(count: int) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"Removed **{count}** song(s) from the playlist.")


def playlist_deleted(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"Deleted playlist **{name}**.")


def playlist_added(name: str, count: int) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"Queuing **{name}** — adding {count} song(s) to the queue.")


def joined_voice(channel_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"Joined **{channel_name}**.")


# ── Error / status messages ───────────────────────────────────────────────────

def playlist_name_taken(name: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"You already have a playlist named **{name}**.")


def song_already_in_playlist() -> discord.ui.LayoutView:
    return build_basic_layout(description="That song is already in this playlist.")


def playlist_full() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="This playlist is full (100 songs max). Remove some songs first."
    )


def nothing_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="Nothing is playing right now. Play a song first, then add it.")


def no_songs_to_play() -> discord.ui.LayoutView:
    return build_basic_layout(description="This playlist has no songs yet. Add some songs first!")


def voice_required() -> discord.ui.LayoutView:
    return build_basic_layout(description="You need to be in a voice channel to play a playlist.")


def join_failed() -> discord.ui.LayoutView:
    return build_basic_layout(description="Failed to join the voice channel. Please try again.")


def different_voice() -> discord.ui.LayoutView:
    return build_basic_layout(description="You must be in the same voice channel as me.")


def queue_full() -> discord.ui.LayoutView:
    return build_basic_layout(description="The queue is full. Please wait for tracks to finish.")


def save_failed() -> discord.ui.LayoutView:
    return build_basic_layout(description="Failed to save. Please try again.")


def playlist_queuing(name: str, count: int) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"Loading **{name}** ({count} songs) into the queue…")


def invalid_link() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="Only **YouTube** and **Spotify** playlist/album links are supported."
    )
