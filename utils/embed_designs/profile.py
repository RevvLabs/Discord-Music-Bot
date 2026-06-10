import discord
from utils.helper_function.embed_layout import build_basic_layout


def db_error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Error", description=f"Failed to fetch profile data: {msg}")


def dj_only_others(role_name: str | None = None) -> discord.ui.LayoutView:
    target = f"the **{role_name}**" if role_name else "the **DJ**"
    return build_basic_layout(
        title="DJ Only",
        description=(
            f"Only members with {target} role can view other users' profiles.\n"
            "You can still view your own with `/profile`."
        ),
    )
