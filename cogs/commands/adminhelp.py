import discord
from discord.ext import commands
from discord.ext.commands import BucketType

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.auto_delete import schedule_delete


# ── Category data ──────────────────────────────────────────────────────────────
# Each entry: (command_usage, description, required_permission)

CATEGORIES = {
    "Server Setup": {
        "emoji": "🔧",
        "desc": "Configure the bot for your server.",
        "commands": [
            ("/setup <text_channel> <voice_channel>", "Set the player text channel and voice channel",    "Administrator"),
            ("/clearsetup",                           "Remove the channel setup for this server",         "Administrator"),
            ("/getsetup",                             "View the currently configured channels",           "Administrator"),
            ("/temp-setup <text_channel> <category>", "Restrict bot to a text channel + VC category (alternative to /setup)", "Administrator"),
            ("/clear-tempsetup",                      "Remove the temp setup for this server",            "Administrator"),
            ("/get-tempsetup",                        "View the current temp setup",                      "Administrator"),
            ("/button",                               "Toggle player control buttons on/off in the card", "Administrator"),
        ],
    },
    "DJ Role": {
        "emoji": "🎧",
        "desc": "Assign and manage the DJ role for your server.",
        "commands": [
            ("/djset [role]", "Set the DJ role (no argument = show current)", "Manage Server"),
            ("/djclear",      "Remove the DJ role from the server",           "Manage Server"),
        ],
    },
    "DJ Command Lock": {
        "emoji": "🔒",
        "desc": "Control which commands require the DJ role per server.",
        "commands": [
            ("/djlock <command>",   "Lock a command so only the DJ role can use it",               "Manage Server"),
            ("/djunlock <command>", "Unlock a command so everyone can use it",                     "Manage Server"),
            ("/djlockstatus",       "Show all currently locked/unlocked commands for this server", "Anyone"),
        ],
    },
    "Bot Owner": {
        "emoji": "👑",
        "desc": "Commands restricted to the bot owner only.",
        "commands": [
            ("/autoplaymanager",    "Manage bot-curated autoplay playlists",              "Bot Owner"),
            ("/engine-control",     "Enable or disable individual search engines",        "Bot Owner"),
            ("/lock <command>",     "Lock a command globally for maintenance",            "Bot Owner"),
            ("/unlock <command>",   "Unlock a command from maintenance",                  "Bot Owner"),
            ("/locked",             "List all commands currently locked for maintenance", "Bot Owner"),
            ("/forcefix",           "Force-fix all voice connections across all guilds",  "Bot Owner"),
            ("/unblacklist <user>", "Remove a user from the blacklist",                   "Bot Owner"),
            ("/backup",             "Backup .env, emojis.py, and the database to DMs",   "Bot Owner"),
            ("/debugbot",           "Toggle detailed voltricx debug logging",             "Bot Owner"),
            ("/node",               "Display Lavalink node info (compact)",               "Bot Owner"),
            ("/realnode",           "Display detailed Lavalink node info",                "Bot Owner"),
            ("/visualiser",         "Visualise all owner commands and their status",      "Bot Owner"),
            ("cache stats",         "Show unified cache statistics",                      "Bot Owner"),
            ("cache export",        "Export full cache data to a file",                   "Bot Owner"),
            ("cache cacheclear",    "Clear all in-memory cache data",                     "Bot Owner"),
        ],
    },
    "Utilities": {
        "emoji": "🛠️",
        "desc": "General-purpose utilities for server managers.",
        "commands": [
            ("/fix", "Fix the bot's voice connection in this server", "Anyone in VC"),
        ],
    },
}

OVERVIEW_ORDER = list(CATEGORIES.keys())


def _build_container(category: str | None) -> discord.ui.Container:
    if category and category in CATEGORIES:
        cat = CATEGORIES[category]
        lines = "\n".join(
            f"`{cmd}` — {desc}\n> *Requires: {perm}*"
            for cmd, desc, perm in cat["commands"]
        )
        return discord.ui.Container(
            discord.ui.TextDisplay(content=f"## {cat['emoji']} {category}"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=f"*{cat['desc']}*\n\n{lines}"),
            discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="*Use the dropdown to switch categories.*"),
            accent_color=EMBED_COLOR,
        )

    # Overview
    total = sum(len(v["commands"]) for v in CATEGORIES.values())
    lines = "\n".join(
        f"{v['emoji']} **{cat}** — {len(v['commands'])} command{'s' if len(v['commands']) != 1 else ''}"
        for cat, v in CATEGORIES.items()
    )
    return discord.ui.Container(
        discord.ui.TextDisplay(content="## ⚙️ Admin & Owner Help"),
        discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(
            content=f"Commands for server admins, managers, and the bot owner.\n\n{lines}\n\n*{total} total commands*"
        ),
        discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small),
        discord.ui.TextDisplay(content="*Select a category from the dropdown below.*"),
        accent_color=EMBED_COLOR,
    )


class AdminHelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label="Overview", value="overview", description="Summary of all categories", emoji="📋")]
        for cat, v in CATEGORIES.items():
            options.append(discord.SelectOption(
                label=cat,
                value=cat,
                description=v["desc"][:50],
                emoji=v["emoji"],
            ))
        super().__init__(placeholder="Select a category…", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        cat = None if selected == "overview" else selected

        view = discord.ui.LayoutView()
        view.add_item(_build_container(cat))
        row = discord.ui.ActionRow()
        row.add_item(AdminHelpDropdown())
        view.add_item(row)

        await interaction.response.edit_message(view=view)


class AdminHelpView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=120)
        self.message: discord.Message | None = None
        self.add_item(_build_container(None))
        row = discord.ui.ActionRow()
        row.add_item(AdminHelpDropdown())
        self.add_item(row)

    async def on_timeout(self):
        if self.message:
            try:
                v = discord.ui.LayoutView()
                v.add_item(discord.ui.Container(
                    discord.ui.TextDisplay(content="⏳ Closed — inactive for too long."),
                    accent_color=discord.Color.from_rgb(128, 128, 128),
                ))
                await self.message.edit(view=v)
            except Exception:
                pass


class AdminHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="adminhelp",
        description="Show all admin, DJ, and bot-owner commands.",
        aliases=["ahelp", "adminh"],
    )
    @commands.cooldown(1, 5, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def adminhelp(self, ctx: commands.Context):
        view = AdminHelpView()
        msg = await ctx.send(view=view, ephemeral=True)
        view.message = msg


async def setup(bot):
    await bot.add_cog(AdminHelp(bot))
