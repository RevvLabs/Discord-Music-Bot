import discord
from utils.helper_function.embed_layout import build_basic_layout


def db_error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Error", description=f"Failed to fetch profile data: {msg}")


def card_text_fallback(
    display_name: str,
    badge: str,
    total_songs: int,
    listening_time: str,
    server_rank,
    server_songs: int,
    fav_count: int,
    playlist_count: int,
    top_sources: list,
    guild_name: str,
) -> discord.ui.LayoutView:
    """Text-only profile, used when image uploads are blocked for the guild."""
    rank_str = f"#{server_rank}" if server_rank else "N/A"
    src_lines = "\n".join(f"- **{s}** — {c:,}" for s, c in top_sources[:3]) or "- _no data_"
    desc = (
        f"**{display_name}** · *{badge}*\n"
        f"--- \n"
        f"**Overall**\n"
        f"- Listening time: {listening_time}\n"
        f"- Songs streamed: {total_songs:,}\n\n"
        f"**In {guild_name[:30]}**\n"
        f"- Rank: {rank_str}\n"
        f"- Songs here: {server_songs:,}\n\n"
        f"**Library**\n"
        f"- Favorites: {fav_count:,}\n"
        f"- Playlists: {playlist_count:,}\n\n"
        f"**Top sources**\n{src_lines}\n\n"
        f"--- \n"
        f"_Image card unavailable — file uploads are currently limited for this server._"
    )
    return build_basic_layout(title="Music Profile", description=desc)


def dj_only_others(role_name: str | None = None) -> discord.ui.LayoutView:
    target = f"the **{role_name}**" if role_name else "the **DJ**"
    return build_basic_layout(
        title="DJ Only",
        description=(
            f"Only members with {target} role can view other users' profiles.\n"
            "You can still view your own with `/profile`."
        ),
    )
