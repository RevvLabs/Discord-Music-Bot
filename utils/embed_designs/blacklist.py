import discord
from utils.helper_function.embed_layout import build_basic_layout
from utils.colours.embed_text_colours import wrap_yellow

_BLACKLIST_GIF = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExam42b2c5ejFhcW80ZXhta3d0bjZjMHRzbnZrOW5xM3JtZzBydTUzMSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/4BXKwKrbZxVNm/giphy.gif"


def user_blacklisted() -> discord.ui.LayoutView:
    return build_basic_layout(
        title="You have been blacklisted",
        description="You were blacklisted for spamming commands too quickly.",
        image_url=_BLACKLIST_GIF,
    )


def perm_denied() -> discord.ui.LayoutView:
    return build_basic_layout(
        description="### Permission Denied\n" + wrap_yellow("Only Bot Owner Can do this !")
    )


def not_blacklisted(mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="User Not Found", description=f"{mention} is not blacklisted.")


def unblacklisted(mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="User Unblacklisted", description=f"{mention} has been removed from the blacklist.")


def blacklisted(mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="User Blacklisted", description=f"{mention} has been added to the blacklist.")


def already_blacklisted(mention: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Already Blacklisted", description=f"{mention} is already blacklisted.")


def error(msg: str) -> discord.ui.LayoutView:
    return build_basic_layout(title="Error", description=f"An error occurred: {msg}")
