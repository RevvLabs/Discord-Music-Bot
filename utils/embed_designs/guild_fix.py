import discord
from utils.helper_function.embed_layout import build_basic_layout


def connection_fixed() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Connection Fixed\nSuccessfully fixed the voice connection for this guild.")


def no_connection() -> discord.ui.LayoutView:
    return build_basic_layout(description="### No Connection\nNo player/voice connection found in this guild.")


def fix_error() -> discord.ui.LayoutView:
    return build_basic_layout(description="### Error Occurred\nAn error occurred while fixing the connection for this guild. Check console.")
