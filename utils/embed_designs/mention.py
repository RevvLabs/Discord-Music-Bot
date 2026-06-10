import discord
from utils.helper_function.embed_layout import build_basic_layout


def greeting(bot_name: str, prefix: str, setup_info: str) -> discord.ui.LayoutView:
    return build_basic_layout(
        title=f"Hey there! I'm **{bot_name}**, your ultimate music companion!",
        description=(
            f"Bot prefix is set to : `{prefix}`\n\n"
            f"{setup_info}"
            f"Need help? Simply type `{prefix}help` for a full list of commands!\n\n"
            f"--- \nMade with ❤️   •   {bot_name}!"
        ),
    )
