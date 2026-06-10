import discord
from utils.helper_function.bot_config import EMBED_COLOR


def session_over() -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🎶 Music Session Over"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content="That's a wrap! All songs have been played.\n"
                    "Use `/play` to queue up more tracks and keep the party going! 🎉"
        ),
        accent_color=EMBED_COLOR,
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def inactive_player(timeout: int) -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 💤 Disconnected — Inactive"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content=f"The player was inactive for `{timeout}s` with no one listening.\n"
                    "Use `/play` to start a new session!"
        ),
        accent_color=EMBED_COLOR,
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def session_locked(owner_name: str) -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🔒 Session Locked"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content=f"**{owner_name}** has locked this music session.\n\n"
                    "You can't use music commands right now. Ask the DJ to either:\n"
                    f"- Unlock the session → `/session` → **Unlock Session**\n"
                    f"- Add you to the session → `/sessionadd @you`"
        ),
        accent_color=discord.Color.from_rgb(237, 66, 69),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def session_status_public() -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🎵 Session — Public"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="The session is **public**. Everyone in the voice channel can use music commands."),
        accent_color=discord.Color.from_rgb(87, 242, 135),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def session_status_private(owner_name: str) -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🔒 Session — Private"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content=f"The session is **private**, locked by **{owner_name}**.\n"
                    "Only the session owner and server admins can control music."
        ),
        accent_color=discord.Color.from_rgb(237, 66, 69),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def session_now_private(owner_name: str) -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🔒 Session Locked"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content=f"**{owner_name}** has taken control of the session.\n"
                    "Others cannot add, skip, or change music until the session is unlocked."
        ),
        accent_color=discord.Color.from_rgb(237, 66, 69),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def session_now_public() -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🔓 Session Unlocked"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="The session is now **public**. Everyone can use music commands again."),
        accent_color=discord.Color.from_rgb(87, 242, 135),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def session_auto_unlocked(owner_name: str) -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🔓 Session Unlocked"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content=f"**{owner_name}** left the voice channel — session is now public again."
        ),
        accent_color=discord.Color.from_rgb(87, 242, 135),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def not_dj() -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🚫 DJ Only"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="You need the **DJ role** to lock or unlock a session."),
        accent_color=discord.Color.from_rgb(237, 66, 69),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def user_added(user_name: str) -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## ✅ User Added to Session"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content=f"**{user_name}** has been added to the session.\n"
                    "They can now use music commands while the session is locked.\n"
                    "*Note: DJ-locked commands still require the DJ role.*"
        ),
        accent_color=discord.Color.from_rgb(87, 242, 135),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def user_removed(user_name: str) -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🚫 User Removed from Session"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content=f"**{user_name}** has been removed from the session.\n"
                    "They can no longer use music commands while the session is locked."
        ),
        accent_color=discord.Color.from_rgb(128, 128, 128),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def user_already_added(user_name: str) -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## ⚠️ Already in Session"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"**{user_name}** is already in the session."),
        accent_color=discord.Color.from_rgb(254, 231, 92),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def user_not_in_session(user_name: str) -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## ⚠️ Not in Session"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content=f"**{user_name}** was not added to this session."),
        accent_color=discord.Color.from_rgb(254, 231, 92),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def no_active_session() -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## ⚠️ No Active Session"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content="There is no locked session right now.\nUse `/session` to lock one first."
        ),
        accent_color=discord.Color.from_rgb(254, 231, 92),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def not_session_owner_manage() -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🚫 Not the Session Owner"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content="Only the DJ who locked this session can add or remove users."
        ),
        accent_color=discord.Color.from_rgb(237, 66, 69),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view


def not_session_owner() -> discord.ui.LayoutView:
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 🚫 Not the Session Owner"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content="Only the DJ who locked this session (or a server admin) can unlock it."
        ),
        accent_color=discord.Color.from_rgb(237, 66, 69),
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    return view
