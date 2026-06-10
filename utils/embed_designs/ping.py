import discord
from utils.helper_function.embed_layout import build_basic_layout


def pong(bot_latency: float, ws_latency: float) -> discord.ui.LayoutView:
    return build_basic_layout(
        title="Pong!",
        description=(
            f"`Bot Latency  ` : **{bot_latency}ms**\n"
            f"`Websocket Lat` : **{ws_latency}ms**"
        ),
    )
