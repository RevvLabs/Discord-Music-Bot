import discord
from discord.ext import commands
from discord.ext.commands import BucketType

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.dj_checker import dj_check_member
from utils.helper_function.session_manager import session_manager
from utils.embed_designs import session as session_design
from utils.embed_designs import voice_check as vc_design


class SessionView(discord.ui.LayoutView):
    """Interactive session control panel with Lock / Unlock buttons."""

    def __init__(self, ctx: commands.Context, is_locked: bool):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.message: discord.Message | None = None
        self._build(is_locked)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Only the DJ who opened this panel can use it.", ephemeral=True
            )
            return False
        return True

    def _build(self, is_locked: bool):
        self.clear_items()

        info = session_manager.get_info(self.ctx.guild.id)
        if is_locked and info:
            status_text = (
                f"**Status:** 🔒 Private — locked by **{info.owner_name}**\n"
                "Others cannot add, skip, or change music."
            )
        else:
            status_text = "**Status:** 🔓 Public — everyone can use music commands."

        lock_btn = discord.ui.Button(
            label="Lock Session",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            disabled=is_locked,
            custom_id="session_lock",
        )
        unlock_btn = discord.ui.Button(
            label="Unlock Session",
            style=discord.ButtonStyle.success,
            emoji="🔓",
            disabled=not is_locked,
            custom_id="session_unlock",
        )

        close_btn = discord.ui.Button(
            label="✕ Close",
            style=discord.ButtonStyle.secondary,
            custom_id="session_close",
        )
        lock_btn.callback = self._lock_callback
        unlock_btn.callback = self._unlock_callback
        close_btn.callback = self._close_callback

        row = discord.ui.ActionRow()
        row.add_item(lock_btn)
        row.add_item(unlock_btn)
        row.add_item(close_btn)

        container = discord.ui.Container(
            discord.ui.TextDisplay(content="## 🎵 Session Control"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=status_text),
            accent_color=(
                discord.Color.from_rgb(237, 66, 69)
                if is_locked
                else discord.Color.from_rgb(87, 242, 135)
            ),
        )
        self.add_item(container)
        self.add_item(row)

    async def _lock_callback(self, interaction: discord.Interaction):
        allowed, _ = await dj_check_member(interaction.user, interaction.guild)
        if not allowed:
            await interaction.response.send_message(
                view=session_design.not_dj(), ephemeral=True
            )
            return

        if session_manager.is_locked(interaction.guild.id):
            await interaction.response.defer()
            return

        session_manager.lock(interaction.guild.id, interaction.user.id, interaction.user.display_name)
        self._build(True)
        await interaction.response.edit_message(view=self)

    async def _unlock_callback(self, interaction: discord.Interaction):
        info = session_manager.get_info(interaction.guild.id)
        if info is None:
            await interaction.response.defer()
            return

        # Only the owner or admins can unlock
        perms = getattr(interaction.user, "guild_permissions", None)
        is_admin = perms and (perms.administrator or perms.manage_guild)
        import os
        bot_owners = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]
        is_bot_owner = interaction.user.id in bot_owners

        if interaction.user.id != info.owner_id and not is_admin and not is_bot_owner:
            await interaction.response.send_message(
                view=session_design.not_session_owner(), ephemeral=True
            )
            return

        session_manager.unlock(interaction.guild.id)
        self._build(False)
        await interaction.response.edit_message(view=self)

    async def _close_callback(self, interaction: discord.Interaction):
        try:
            await interaction.message.delete()
        except Exception:
            await interaction.response.defer()

    async def on_timeout(self):
        if self.message:
            try:
                cleanup_view = discord.ui.LayoutView()
                cleanup_view.add_item(discord.ui.Container(
                    discord.ui.TextDisplay(content="⏳ Closed — inactive for too long."),
                    accent_color=discord.Color.from_rgb(128, 128, 128),
                ))
                await self.message.edit(view=cleanup_view)
            except Exception:
                pass


class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _check_vc(self, ctx: commands.Context) -> bool:
        """User must be in the bot's voice channel to manage the session.

        Deliberately does NOT use ensure_voice(): its session-lock check would
        block other DJs/admins from ever opening the panel to unlock.
        """
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(view=vc_design.not_in_voice(), ephemeral=True)
            return False
        if not ctx.guild.voice_client:
            await ctx.send(view=vc_design.bot_not_connected(), ephemeral=True)
            return False
        if ctx.guild.voice_client.channel != ctx.author.voice.channel:
            await ctx.send(view=vc_design.different_voice(), ephemeral=True)
            return False
        return True

    @commands.hybrid_command(
        name="session",
        description="Lock or unlock the music session (DJ only).",
        aliases=["sess"],
    )
    @commands.cooldown(1, 3, BucketType.guild)
    @is_not_blacklisted()
    @maintenance_check()
    async def session(self, ctx: commands.Context):
        if not await self._check_vc(ctx):
            return
        allowed, _ = await dj_check_member(ctx.author, ctx.guild)
        if not allowed:
            await ctx.send(view=session_design.not_dj(), ephemeral=True)
            return

        is_locked = session_manager.is_locked(ctx.guild.id)
        view = SessionView(ctx, is_locked)
        msg = await ctx.send(view=view)
        view.message = msg

    @commands.hybrid_command(
        name="sessionadd",
        description="Add a user to the locked session so they can use music commands.",
        aliases=["sadd"],
    )
    @commands.cooldown(1, 3, BucketType.guild)
    @is_not_blacklisted()
    @maintenance_check()
    async def sessionadd(self, ctx: commands.Context, user: discord.Member):
        if not await self._check_vc(ctx):
            return
        info = session_manager.get_info(ctx.guild.id)
        if not info:
            await ctx.send(view=session_design.no_active_session(), ephemeral=True)
            return

        allowed, _ = await dj_check_member(ctx.author, ctx.guild)
        if not allowed or ctx.author.id != info.owner_id:
            await ctx.send(view=session_design.not_session_owner_manage(), ephemeral=True)
            return

        if user.id == info.owner_id:
            await ctx.send(view=session_design.user_already_added(user.display_name), ephemeral=True)
            return

        if user.id in info.allowed_users:
            await ctx.send(view=session_design.user_already_added(user.display_name), ephemeral=True)
            return

        session_manager.add_user(ctx.guild.id, user.id)
        await ctx.send(view=session_design.user_added(user.display_name), ephemeral=True)

    @commands.hybrid_command(
        name="sessionremove",
        description="Remove a user from the locked session.",
        aliases=["sremove", "srem"],
    )
    @commands.cooldown(1, 3, BucketType.guild)
    @is_not_blacklisted()
    @maintenance_check()
    async def sessionremove(self, ctx: commands.Context, user: discord.Member):
        if not await self._check_vc(ctx):
            return
        info = session_manager.get_info(ctx.guild.id)
        if not info:
            await ctx.send(view=session_design.no_active_session(), ephemeral=True)
            return

        allowed, _ = await dj_check_member(ctx.author, ctx.guild)
        if not allowed or ctx.author.id != info.owner_id:
            await ctx.send(view=session_design.not_session_owner_manage(), ephemeral=True)
            return

        if user.id not in info.allowed_users:
            await ctx.send(view=session_design.user_not_in_session(user.display_name), ephemeral=True)
            return

        session_manager.remove_user(ctx.guild.id, user.id)
        await ctx.send(view=session_design.user_removed(user.display_name), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Session(bot))
