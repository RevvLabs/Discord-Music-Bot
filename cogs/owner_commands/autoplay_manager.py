"""
Autoplay Manager — owner/controller-only command to manage bot-curated playlists.

Permission: bot owner OR AUTOPLAY_CONTROLLERS list.

Panel shows:
  • Current playlists (name, platform, track count, who added)
  • [Add Playlist] button → modal (name + link) → prefetch → update panel
  • [Remove Playlist] button → select dropdown → remove confirmation
"""
from __future__ import annotations

import discord
from discord.ext import commands
from discord.ext.commands import BucketType

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.helper_function.autoplay_cache import autoplay_cache
from utils.helper_function.bot_config import EMBED_COLOR
from utils.logger.mewzik_logger import bot_logger
from utils.embed_designs import owner as owner_design

import os
from dotenv import load_dotenv

load_dotenv()

def _has_permission(user_id: int) -> bool:
    owners = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]
    return user_id in owners


def _build_panel_text() -> str:
    playlists = autoplay_cache.get_playlists()
    lines = ["## 🎛️ Autoplay Manager", "Manage bot-curated autoplay playlists.\n"]
    if not playlists:
        lines.append("*No playlists added yet.*")
    else:
        for pl in playlists:
            lines.append(
                f"**{pl['name']}** — {pl['platform']} · {pl['track_count']} tracks"
            )
    return "\n".join(lines)


# ── Modal: Add Playlist ───────────────────────────────────────────────────────

class AddAutoplayPlaylistModal(discord.ui.Modal, title="Add Autoplay Playlist"):
    pl_name = discord.ui.TextInput(
        label="Playlist Name",
        placeholder="e.g. Late Night Vibes",
        max_length=50,
        required=True,
    )
    pl_link = discord.ui.TextInput(
        label="Playlist / Album Link",
        placeholder="Spotify or YouTube playlist URL",
        max_length=500,
        required=True,
    )

    def __init__(self, manager_view: "AutoplayManagerView"):
        super().__init__()
        self._manager = manager_view

    async def on_submit(self, interaction: discord.Interaction):
        name = self.pl_name.value.strip()
        link = self.pl_link.value.strip()

        # Validate platform before doing expensive work
        platform = autoplay_cache._platform(link)
        if platform == "Unknown":
            await interaction.response.send_message(
                "❌ Only **Spotify** and **YouTube** playlist links are supported.",
                ephemeral=True,
            )
            return

        is_sp = autoplay_cache._is_spotify_playlist(link)
        is_yt = autoplay_cache._is_youtube_playlist(link)
        if not is_sp and not is_yt:
            await interaction.response.send_message(
                "❌ Please provide a **playlist** or **album** link, not a single track.",
                ephemeral=True,
            )
            return

        # Acknowledge immediately — prefetch may take a while (Spotify = 1 search/track)
        await interaction.response.send_message(
            f"⏳ Fetching **{name}** from {platform}… this may take a moment for large playlists.",
            ephemeral=True,
        )

        ok, count, err = await autoplay_cache.add_playlist(
            name=name,
            link=link,
            added_by=interaction.user.id,
        )

        if not ok:
            await interaction.edit_original_response(
                content=f"❌ Failed to add **{name}**: {err}"
            )
            return

        await interaction.edit_original_response(
            content=f"✅ Added **{name}** ({platform} · {count} tracks) to autoplay playlists!"
        )

        # Refresh the manager panel
        try:
            await self._manager.refresh(interaction)
        except Exception:
            pass

        if bot_logger.enabled:
            bot_logger.debug(
                "Autoplay manager — playlist added",
                name=name,
                platform=platform,
                tracks=count,
                user_id=interaction.user.id,
            )


# ── Select: Remove playlist picker ───────────────────────────────────────────

class RemoveAutoplaySelect(discord.ui.Select):
    def __init__(self, playlists: list, manager_view: "AutoplayManagerView"):
        self._manager = manager_view
        options = [
            discord.SelectOption(
                label=pl["name"][:100],
                value=pl["id"],
                description=f"{pl['platform']} · {pl['track_count']} tracks",
            )
            for pl in playlists[:25]
        ]
        super().__init__(
            placeholder="Select a playlist to remove…",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        playlist_id = self.values[0]
        pl = autoplay_cache.get_playlist_by_id(playlist_id)
        name = pl["name"] if pl else playlist_id

        removed = autoplay_cache.remove_playlist(playlist_id)
        if removed:
            await interaction.response.send_message(
                f"🗑️ Removed **{name}** from autoplay playlists.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Could not remove **{name}**. It may have already been deleted.",
                ephemeral=True,
            )

        # Refresh the manager panel
        try:
            await self._manager.refresh(interaction)
        except Exception:
            pass

        if bot_logger.enabled:
            bot_logger.debug(
                "Autoplay manager — playlist removed",
                name=name,
                playlist_id=playlist_id,
                user_id=interaction.user.id,
            )


# ── Buttons ───────────────────────────────────────────────────────────────────

class AddPlaylistButton(discord.ui.Button):
    def __init__(self, manager_view: "AutoplayManagerView"):
        super().__init__(label="Add Playlist ➕", style=discord.ButtonStyle.green)
        self._manager = manager_view

    async def callback(self, interaction: discord.Interaction):
        if not _has_permission(interaction.user.id):
            await interaction.response.send_message(
                "❌ You don't have permission to manage autoplay playlists.", ephemeral=True
            )
            return
        await interaction.response.send_modal(AddAutoplayPlaylistModal(self._manager))


class RemovePlaylistButton(discord.ui.Button):
    def __init__(self, manager_view: "AutoplayManagerView"):
        super().__init__(label="Remove Playlist 🗑️", style=discord.ButtonStyle.red)
        self._manager = manager_view

    async def callback(self, interaction: discord.Interaction):
        if not _has_permission(interaction.user.id):
            await interaction.response.send_message(
                "❌ You don't have permission to manage autoplay playlists.", ephemeral=True
            )
            return

        playlists = autoplay_cache.get_playlists()
        if not playlists:
            await interaction.response.send_message(
                "No playlists to remove.", ephemeral=True
            )
            return

        remove_view = discord.ui.LayoutView(timeout=30)
        remove_row = discord.ui.ActionRow()
        remove_row.add_item(RemoveAutoplaySelect(playlists, self._manager))
        remove_view.add_item(remove_row)
        await interaction.response.send_message(view=remove_view, ephemeral=True)


# ── Manager panel view ────────────────────────────────────────────────────────

class AutoplayManagerView(discord.ui.LayoutView):
    def __init__(self, author_id: int, message: discord.Message = None):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.message = message
        self._build()

    def _build(self):
        # Clear existing items before rebuild
        self._children.clear()

        # Header container
        panel_text = _build_panel_text()
        header = discord.ui.Container(discord.ui.TextDisplay(content=panel_text), accent_color=EMBED_COLOR)
        self.add_item(header)

        # Button row
        button_row = discord.ui.ActionRow()
        button_row.add_item(AddPlaylistButton(self))
        button_row.add_item(RemovePlaylistButton(self))
        self.add_item(button_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the command invoker can use this panel.", ephemeral=True
            )
            return False
        return True

    async def refresh(self, interaction: discord.Interaction):
        """Rebuild panel text and edit the original manager message."""
        self._build()
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    async def on_timeout(self):
        try:
            if self.message:
                for item in self._children:
                    if hasattr(item, "disabled"):
                        item.disabled = True
                await self.message.edit(view=self)
        except Exception:
            pass


# ── Cog ───────────────────────────────────────────────────────────────────────

class AutoplayManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="autoplaymanager",
        description="Manage bot-curated autoplay playlists (admin only).",
        aliases=["apm"],
    )
    @commands.cooldown(1, 5, BucketType.user)
    @is_not_blacklisted()
    async def autoplaymanager(self, ctx: commands.Context):
        if not _has_permission(ctx.author.id):
            await ctx.send(view=owner_design.autoplay_mgr_permission_denied(), ephemeral=True)
            return

        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)
            message = await ctx.interaction.followup.send("Loading…", ephemeral=True)
        else:
            message = await ctx.send("Loading…")

        panel_view = AutoplayManagerView(ctx.author.id, message=message)
        await message.edit(content=None, view=panel_view)

        if bot_logger.enabled:
            bot_logger.debug(
                "Autoplay manager panel opened",
                user_id=ctx.author.id,
                guild_id=ctx.guild.id,
            )


async def setup(bot):
    await bot.add_cog(AutoplayManager(bot))
