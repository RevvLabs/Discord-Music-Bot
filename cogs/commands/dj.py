import discord
from discord.ext import commands
from discord.ext.commands import BucketType

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.dj_checker import DEFAULT_DJ_LOCKED_COMMANDS
from utils.helper_function.unified_cache_manager import unified_cache
from utils.embed_designs import dj as dj_design
from utils.helper_function.auto_delete import schedule_delete


class DJ(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─── DJ role management ────────────────────────────────────────────────────

    @commands.hybrid_command(
        name="djset",
        description="Set the DJ role. Members with this role skip tracks instantly (no vote).",
        aliases=["setdj"],
    )
    @commands.cooldown(1, 3, BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    @is_not_blacklisted()
    @maintenance_check()
    async def djset(self, ctx: commands.Context, role: discord.Role = None):
        """Set the DJ role, or show the current one when no role is given."""
        if role is None:
            current_id = await unified_cache.get_dj_role(ctx.guild.id)
            role_name = None
            if current_id:
                existing = ctx.guild.get_role(current_id)
                role_name = existing.name if existing else f"{current_id} (deleted role)"
            await ctx.send(view=dj_design.dj_role_status(role_name), ephemeral=True)
            return

        ok = await unified_cache.set_dj_role(ctx.guild.id, role.id)
        if ok:
            schedule_delete(await ctx.send(view=dj_design.dj_role_set(role.name)))
        else:
            await ctx.send(view=dj_design.save_failed(), ephemeral=True)

    @commands.hybrid_command(
        name="djclear",
        description="Remove the DJ role — everyone goes back to vote-to-skip.",
        aliases=["cleardj"],
    )
    @commands.cooldown(1, 3, BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    @is_not_blacklisted()
    @maintenance_check()
    async def djclear(self, ctx: commands.Context):
        ok = await unified_cache.clear_dj_role(ctx.guild.id)
        if ok:
            schedule_delete(await ctx.send(view=dj_design.dj_role_cleared()))
        else:
            await ctx.send(view=dj_design.save_failed(), ephemeral=True)

    # ─── Command lock management ───────────────────────────────────────────────

    @commands.hybrid_command(
        name="djlock",
        description="Lock a command so only the DJ role can use it.",
        aliases=["lockdj"],
    )
    @commands.cooldown(1, 3, BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    @is_not_blacklisted()
    @maintenance_check()
    async def djlock(self, ctx: commands.Context, command: str):
        """Lock <command> to the DJ role for this server."""
        command = command.lstrip("/").lower()

        # Check if the command actually exists on the bot
        if not self.bot.get_command(command):
            await ctx.send(
                view=dj_design.save_failed(),
                ephemeral=True,
            )
            return

        overrides = await unified_cache.get_command_dj_overrides(ctx.guild.id)
        already_locked = overrides.get(command, command in DEFAULT_DJ_LOCKED_COMMANDS)
        if already_locked:
            await ctx.send(view=dj_design.command_already_locked(command), ephemeral=True)
            return

        ok = await unified_cache.set_command_dj_lock(ctx.guild.id, command, True)
        if not ok:
            await ctx.send(view=dj_design.save_failed(), ephemeral=True)
            return

        dj_role_id = await unified_cache.get_dj_role(ctx.guild.id)
        if not dj_role_id:
            schedule_delete(await ctx.send(view=dj_design.no_dj_role_warning(command)))
        else:
            schedule_delete(await ctx.send(view=dj_design.command_locked(command)))

    @commands.hybrid_command(
        name="djunlock",
        description="Unlock a command so everyone can use it (removes DJ restriction).",
        aliases=["unlockdj"],
    )
    @commands.cooldown(1, 3, BucketType.guild)
    @commands.has_permissions(manage_guild=True)
    @is_not_blacklisted()
    @maintenance_check()
    async def djunlock(self, ctx: commands.Context, command: str):
        """Unlock <command> for everyone in this server."""
        command = command.lstrip("/").lower()

        if not self.bot.get_command(command):
            await ctx.send(view=dj_design.save_failed(), ephemeral=True)
            return

        overrides = await unified_cache.get_command_dj_overrides(ctx.guild.id)
        already_unlocked = not overrides.get(command, command in DEFAULT_DJ_LOCKED_COMMANDS)
        if already_unlocked:
            await ctx.send(view=dj_design.command_already_unlocked(command), ephemeral=True)
            return

        ok = await unified_cache.set_command_dj_lock(ctx.guild.id, command, False)
        if ok:
            schedule_delete(await ctx.send(view=dj_design.command_unlocked(command)))
        else:
            await ctx.send(view=dj_design.save_failed(), ephemeral=True)

    @commands.hybrid_command(
        name="djlockstatus",
        description="Show which commands are DJ-locked in this server.",
        aliases=["djstatus", "lockstatus"],
    )
    @commands.cooldown(1, 5, BucketType.guild)
    @is_not_blacklisted()
    @maintenance_check()
    async def djlockstatus(self, ctx: commands.Context):
        """Show the effective DJ lock state for every command in this server."""
        overrides = await unified_cache.get_command_dj_overrides(ctx.guild.id)

        # Collect all command names known to this bot
        all_command_names = {cmd.name for cmd in self.bot.commands}

        locked_commands = []
        unlocked_overrides = []

        for name in all_command_names:
            if name in overrides:
                if overrides[name]:
                    locked_commands.append(name)
                else:
                    # Explicitly unlocked — only notable if it was default-locked
                    if name in DEFAULT_DJ_LOCKED_COMMANDS:
                        unlocked_overrides.append(name)
            elif name in DEFAULT_DJ_LOCKED_COMMANDS:
                locked_commands.append(name)

        await ctx.send(
            view=dj_design.lock_status(locked_commands, unlocked_overrides),
            ephemeral=True,
        )

    # ─── Autocomplete ──────────────────────────────────────────────────────────

    @djlock.autocomplete("command")
    async def djlock_autocomplete(self, interaction: discord.Interaction, current: str):
        names = sorted(cmd.name for cmd in self.bot.commands)
        return [
            discord.app_commands.Choice(name=n, value=n)
            for n in names
            if current.lower() in n.lower()
        ][:25]

    @djunlock.autocomplete("command")
    async def djunlock_autocomplete(self, interaction: discord.Interaction, current: str):
        names = sorted(cmd.name for cmd in self.bot.commands)
        return [
            discord.app_commands.Choice(name=n, value=n)
            for n in names
            if current.lower() in n.lower()
        ][:25]

    # ─── Error handlers ────────────────────────────────────────────────────────

    @djset.error
    async def djset_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(view=dj_design.no_permission(), ephemeral=True)

    @djclear.error
    async def djclear_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(view=dj_design.no_permission(), ephemeral=True)

    @djlock.error
    async def djlock_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(view=dj_design.no_permission(), ephemeral=True)

    @djunlock.error
    async def djunlock_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(view=dj_design.no_permission(), ephemeral=True)


async def setup(bot):
    await bot.add_cog(DJ(bot))
