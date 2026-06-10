import discord
from utils.helper_function.bot_config import EMBED_COLOR, BOT_NAME


def _latency_bar(ms: float) -> str:
    if ms <= 80:
        return "🟢"
    elif ms <= 200:
        return "🟡"
    return "🔴"


def _fmt(n: int) -> str:
    return f"{n:,}"


def stats_card(
    uptime_string: str,
    system_info: str,
    cpu_usage: float,
    memory_usage: float,
    ws_latency: float,
    msg_latency: float,
    db_latency: float,
    server_count: int,
    user_count: int,
    global_songs_played: int,
    global_minutes_listening: int,
    bot_avatar_url: str,
) -> discord.ui.LayoutView:
    system_text = (
        f"> ⏱️  **Uptime**   : `{uptime_string}`\n"
        f"> 💻 **System**   : `{system_info}`\n"
        f"> ⚡ **CPU**      : `{cpu_usage:.1f}%`\n"
        f"> 🧠 **RAM**      : `{memory_usage:.1f} MB`"
    )
    network_text = (
        f"> {_latency_bar(ws_latency)} **WebSocket** : `{ws_latency} ms`\n"
        f"> {_latency_bar(msg_latency)} **Message**   : `{msg_latency} ms`\n"
        f"> {_latency_bar(db_latency)} **Database**   : `{db_latency} ms`"
    )
    reach_text = (
        f"> 🏠 **Servers** : `{_fmt(server_count)}`\n"
        f"> 👥 **Users**   : `{_fmt(user_count)}`"
    )
    records_text = (
        f"> ▶️ **Songs Played**     : `{_fmt(global_songs_played)}`\n"
        f"> ⏳ **Minutes Listened** : `{_fmt(global_minutes_listening)}`"
    )

    container = discord.ui.Container(
        discord.ui.Section(
            "## 📊 Bot Statistics",
            f"*Live metrics for {BOT_NAME}*",
            accessory=discord.ui.Thumbnail(bot_avatar_url),
        ),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**🖥️  System**"),
        discord.ui.TextDisplay(content=system_text),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**🌐  Network**"),
        discord.ui.TextDisplay(content=network_text),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**🌍  Reach**"),
        discord.ui.TextDisplay(content=reach_text),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="**🎵  Global Records**"),
        discord.ui.TextDisplay(content=records_text),
        accent_color=EMBED_COLOR,
    )

    view = discord.ui.LayoutView()
    view.add_item(container)
    return view
