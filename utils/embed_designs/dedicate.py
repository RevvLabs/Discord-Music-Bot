import discord
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.embed_layout import build_basic_layout


def dedication_card(track, from_user, to_user) -> discord.ui.LayoutView:
    title = track.title[:60] + ("…" if len(track.title) > 60 else "")
    duration_ms = track.length or 0
    mins, secs = divmod(duration_ms // 1000, 60)
    duration_str = f"{mins:02}m {secs:02}s"

    track_line = f"**[{title}]({track.uri})**" if track.uri else f"**{title}**"
    track_body = f"{track_line}\n{track.author} · {duration_str}"

    dedication_body = (
        f"💌 From : {from_user.mention}\n"
        f"🎯 To      : {to_user.mention}\n\n"
        "*A little something to brighten your day! 🎶*"
    )

    items = [discord.ui.TextDisplay(content="## 💝 Song Dedicated")]
    items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))

    if track.artwork:
        items.append(
            discord.ui.Section(track_body, accessory=discord.ui.Thumbnail(track.artwork))
        )
    else:
        items.append(discord.ui.TextDisplay(content=track_body))

    items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    items.append(discord.ui.TextDisplay(content=dedication_body))

    container = discord.ui.Container(*items, accent_color=EMBED_COLOR)
    view = discord.ui.LayoutView()
    view.add_item(container)

    return view


# ── Error / status messages ───────────────────────────────────────────────────

def not_in_voice() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### Error\nYou need to be in the voice channel to use this command."
    )


def joined_voice(channel_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### Joined VC\nSuccessfully joined **{channel_name}** and ready to play."
    )


def different_voice() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### Error\nYou need to be in the same voice channel as me to use this command."
    )


def no_results(song_name: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        description=f"### No Results\nCould not find any tracks matching: **{song_name}**"
    )


def queue_full() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### Queue Full\nThe queue has reached its maximum capacity. "
                    "Please wait for tracks to finish."
    )
