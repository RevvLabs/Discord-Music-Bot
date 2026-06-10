import discord
from utils.helper_function.bot_config import EMBED_COLOR


def leaderboard_card(guild_name: str, description: str) -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## 🏆 {guild_name} Leaderboard"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=description),
        accent_color=EMBED_COLOR,
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def leaderboard_empty() -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🏆 Leaderboard"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content="No data available for this server yet.\n"
                    "Start playing music to climb the ranks!"
        ),
        accent_color=EMBED_COLOR,
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view
