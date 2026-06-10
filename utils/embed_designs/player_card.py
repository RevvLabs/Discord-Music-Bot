import discord
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.embed_layout import build_basic_layout


# ── Track info text ────────────────────────────────────────────────────────────

def track_info_text(
    playing_emoji: str,
    title: str,
    uri: str,
    author: str,
    duration: str,
    requester_name: str,
) -> str:
    """Returns the markdown body shown inside the player card."""
    short = title[:50] + ("…" if len(title) > 50 else "")
    return (
        f"## {playing_emoji} [{short}]({uri})\n"
        f"> Artist : **{author}**\n"
        f"> Time   : **{duration}**\n"
        f"> Req    : **{requester_name}**"
    )


def track_info_text_full(
    playing_emoji: str,
    title: str,
    uri: str,
    author: str,
    duration: str,
    requester_name: str,
    volume: int,
    autoplay_on: bool = False,
    loop_text: str = "",
    filter_text: str = "",
) -> str:
    """Extended variant used in controls-hidden mode (includes vol/loop/filter)."""
    short = title[:50] + ("…" if len(title) > 50 else "")
    autoplay = "\n> Auto-Play : **On**" if autoplay_on else ""
    return (
        f"## {playing_emoji} [{short}]({uri})\n"
        f"> Artist : **{author}**\n"
        f"> Time   : **{duration}**\n"
        f"> Req    : **{requester_name}**\n"
        f"> Vol    : **{volume}%**"
        f"{autoplay}{loop_text}{filter_text}"
    )


# ── Container builders ────────────────────────────────────────────────────────

def build_player_container(
    header_text: str,
    track_info_content: str,
    artwork_url: str | None,
    control_row_1: discord.ui.ActionRow,
    control_row_2: discord.ui.ActionRow,
) -> discord.ui.Container:
    """Full player container with controls."""
    header = discord.ui.TextDisplay(content=header_text)
    sep = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)

    lines = track_info_content.split("\n", 1)
    info_title = lines[0]
    info_body = lines[1] if len(lines) > 1 else ""

    if artwork_url:
        track_block = discord.ui.Section(info_title, info_body, accessory=discord.ui.Thumbnail(artwork_url))
    else:
        track_block = discord.ui.TextDisplay(content=track_info_content)

    return discord.ui.Container(
        header, sep, track_block,
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        control_row_1, control_row_2,
        accent_color=EMBED_COLOR,
    )


def build_controls_hidden_container(
    header_text: str,
    track_info_content: str,
    artwork_url: str | None,
) -> discord.ui.Container:
    """Compact container used when controls are hidden."""
    header = discord.ui.TextDisplay(content=header_text)
    sep = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)

    lines = track_info_content.split("\n", 1)
    info_title = lines[0]
    info_body = lines[1] if len(lines) > 1 else ""

    if artwork_url:
        track_block = discord.ui.Section(info_title, info_body, accessory=discord.ui.Thumbnail(artwork_url))
    else:
        track_block = discord.ui.TextDisplay(content=track_info_content)

    return discord.ui.Container(
        header, sep, track_block,
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        accent_color=EMBED_COLOR,
    )


def build_settings_container(
    volume: int,
    loop_row: discord.ui.ActionRow,
    misc_row: discord.ui.ActionRow,
    vol_row: discord.ui.ActionRow,
    filter_row: discord.ui.ActionRow,
) -> discord.ui.Container:
    """Settings panel container — labels and separators defined here."""
    return discord.ui.Container(
        discord.ui.TextDisplay(content="## Player Settings"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**Loop Mode**"),
        loop_row,
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**AutoPlay  ·  Queue**"),
        misc_row,
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"**Volume** — `{volume}%`"),
        vol_row,
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**Audio Filter**"),
        filter_row,
        accent_color=EMBED_COLOR,
    )


# ── Ephemeral feedback messages ───────────────────────────────────────────────

def favorite_added(track_title: str, track_uri: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        title="❤️ Added to Favorites",
        description=f"[{track_title}]({track_uri})\n\nUse `/fav` command to view your favorites.",
    )


def favorite_error(error: str) -> discord.ui.LayoutView:
    return build_basic_layout(description=f"Error: Failed to save favorite: {error}")


def player_stopped(mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        title="Stopped Playing",
        description=f"The player has been disconnected by {mention}.",
    )


def not_in_voice() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="You must be connected to a voice channel to use this command."
    )


def different_voice() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="You must be in the same voice channel as the bot to use these controls."
    )


def no_previous_track() -> discord.ui.LayoutView:
    return build_basic_layout(description="No previous track to play.")


def history_reset() -> discord.ui.LayoutView:
    return build_basic_layout(description="No more tracks found in history. Index reset.")


def no_track_playing() -> discord.ui.LayoutView:
    return build_basic_layout(description="No track is currently playing.")
