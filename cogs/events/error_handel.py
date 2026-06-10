import discord
from discord.ext import commands
from discord.ui import Button, View
from discord.ext.commands import CommandOnCooldown
import asyncio
import os
import traceback
from dotenv import load_dotenv
from utils.check_decorators.maintenance import MaintenanceModeActive, CommandUnderMaintenance
from utils.check_decorators.blacklist_checker import UserBlacklisted
from utils.check_decorators.dj_checker import NotDJ
from utils.logger.mewzik_logger import bot_logger
from utils.embed_designs import error_handler as err_design

load_dotenv()

cooldown_replies = {}

_errorhandler_setup_lock = asyncio.Lock()
_original_ctx_send = commands.Context.send
_original_ctx_reply = commands.Context.reply

async def _ctx_send_safe(self: commands.Context, *args, **kwargs):
    inter = getattr(self, "interaction", None)
    try:
        if inter is not None and not inter.response.is_done():
            return await inter.response.send_message(*args, **kwargs)
        if inter is not None:
            return await inter.followup.send(*args, **kwargs)
        return await _original_ctx_send(self, *args, **kwargs)
    except discord.NotFound:
        kw = dict(kwargs)
        kw.pop("ephemeral", None)
        try:
            return await self.channel.send(*args, **kw)
        except Exception:
            return None
    except Exception:
        kw = dict(kwargs)
        kw.pop("ephemeral", None)
        try:
            return await self.channel.send(*args, **kw)
        except Exception:
            return None

async def _ctx_reply_safe(self: commands.Context, *args, **kwargs):
    inter = getattr(self, "interaction", None)
    try:
        if inter is not None and not inter.response.is_done():
            return await inter.response.send_message(*args, **kwargs)
        if inter is not None:
            return await inter.followup.send(*args, **kwargs)
        return await _original_ctx_reply(self, *args, **kwargs)
    except discord.NotFound:
        kw = dict(kwargs)
        kw.pop("ephemeral", None)
        try:
            return await _original_ctx_reply(self, *args, **kw)
        except Exception:
            try:
                return await self.channel.send(*args, **kw)
            except Exception:
                return None
    except Exception:
        kw = dict(kwargs)
        kw.pop("ephemeral", None)
        try:
            return await _original_ctx_reply(self, *args, **kw)
        except Exception:
            try:
                return await self.channel.send(*args, **kw)
            except Exception:
                return None

def _install_ctx_send_patch():
    if commands.Context.send is not _ctx_send_safe:
        commands.Context.send = _ctx_send_safe
    if commands.Context.reply is not _ctx_reply_safe:
        commands.Context.reply = _ctx_reply_safe

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _safe_send(self, ctx, **kwargs):
        inter = getattr(ctx, "interaction", None)
        try:
            if inter is not None and not inter.response.is_done():
                return await inter.response.send_message(**kwargs)
            if inter is not None:
                return await inter.followup.send(**kwargs)
            return await ctx.send(**kwargs)
        except discord.NotFound:
            try:
                return await ctx.channel.send(**kwargs)
            except Exception:
                return None
        except Exception:
            try:
                return await ctx.channel.send(**kwargs)
            except Exception:
                return None

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        original = getattr(error, "original", error)

        try:
            async def send_msg(**kwargs):
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(**kwargs)
                    else:
                        await interaction.followup.send(**kwargs)
                except Exception:
                    pass

            if isinstance(original, CommandUnderMaintenance):
                print(f"\033[91m[ERROR] Command Locked (slash)\033[0m: {original.command_name}")
                await send_msg(view=err_design.command_maintenance(original.command_name, original.reason), ephemeral=True)
            elif isinstance(original, MaintenanceModeActive):
                print("\033[91m[ERROR] Maintenance Mode (slash)\033[0m: Bot is in maintenance mode")
                await send_msg(view=err_design.maintenance_mode(), ephemeral=True)
            elif isinstance(original, UserBlacklisted):
                await send_msg(view=err_design.blacklisted(), ephemeral=True)
            elif isinstance(original, NotDJ):
                role_name = None
                if interaction.guild and original.role_id:
                    role = interaction.guild.get_role(original.role_id)
                    role_name = role.name if role else None
                await send_msg(view=err_design.dj_role_required(role_name), ephemeral=True)
        except Exception as exc:
            print(f"\033[91m[ERROR] on_app_command_error handler\033[0m: {exc}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        global cooldown_replies
        try:
            print(f"\033[91m[ERROR] Command Error\033[0m: {type(error).__name__}: {error}")

            if isinstance(error, CommandOnCooldown):
                user_id = ctx.author.id
                if user_id in cooldown_replies:
                    return
                cooldown_replies[user_id] = True

                if bot_logger.enabled:
                    await bot_logger.async_warning(
                        "Command on cooldown",
                        user_id=ctx.author.id,
                        user=str(ctx.author),
                        command=ctx.command.name if ctx.command else "unknown",
                        retry_after_s=round(error.retry_after, 2),
                        guild_id=ctx.guild.id if ctx.guild else None,
                    )

                await self._safe_send(ctx, view=err_design.cooldown(round(error.retry_after, 2)))
                await asyncio.sleep(4)
                cooldown_replies.pop(user_id, None)
            elif isinstance(error, commands.MissingPermissions):
                print(f"\033[91m[ERROR] Missing Permissions\033[0m: User {ctx.author} lacks required permissions")
                if bot_logger.enabled:
                    await bot_logger.async_error(
                        "Missing permissions",
                        user_id=ctx.author.id,
                        user=str(ctx.author),
                        command=ctx.command.name if ctx.command else "unknown",
                        guild_id=ctx.guild.id if ctx.guild else None,
                        missing=str(error.missing_permissions),
                    )
                await self._safe_send(ctx, view=err_design.missing_permissions())
            elif isinstance(error, commands.CommandNotFound):
                return
            elif isinstance(error, commands.MissingRequiredArgument):
                print(f"\033[91m[ERROR] Missing Required Argument\033[0m: {error.param.name}")
                if bot_logger.enabled:
                    await bot_logger.async_error(
                        "Missing required argument",
                        user_id=ctx.author.id,
                        command=ctx.command.name if ctx.command else "unknown",
                        missing_param=error.param.name,
                        guild_id=ctx.guild.id if ctx.guild else None,
                    )
                await self._safe_send(ctx, view=err_design.missing_argument())
            elif isinstance(error, CommandUnderMaintenance):
                print(f"\033[91m[ERROR] Command Locked\033[0m: {error.command_name} — {error.reason}")
                if bot_logger.enabled:
                    await bot_logger.async_warning(
                        "Command blocked — under maintenance",
                        user_id=ctx.author.id,
                        command=error.command_name,
                        guild_id=ctx.guild.id if ctx.guild else None,
                    )
                await self._safe_send(ctx, view=err_design.command_maintenance(error.command_name, error.reason))
            elif isinstance(error, MaintenanceModeActive):
                print("\033[91m[ERROR] Maintenance Mode\033[0m: Bot is in maintenance mode")
                if bot_logger.enabled:
                    await bot_logger.async_warning(
                        "Command blocked — maintenance mode active",
                        user_id=ctx.author.id,
                        command=ctx.command.name if ctx.command else "unknown",
                        guild_id=ctx.guild.id if ctx.guild else None,
                    )
                await self._safe_send(ctx, view=err_design.maintenance_mode())
            elif isinstance(error, UserBlacklisted):
                print(f"\033[91m[ERROR] User Blacklisted\033[0m: User {ctx.author} is blacklisted")
                if bot_logger.enabled:
                    await bot_logger.async_error(
                        "Blocked — user is blacklisted",
                        user_id=ctx.author.id,
                        user=str(ctx.author),
                        command=ctx.command.name if ctx.command else "unknown",
                        guild_id=ctx.guild.id if ctx.guild else None,
                    )
                await self._safe_send(ctx, view=err_design.blacklisted())
            elif isinstance(error, NotDJ):
                role_name = None
                if ctx.guild and error.role_id:
                    role = ctx.guild.get_role(error.role_id)
                    role_name = role.name if role else None
                if bot_logger.enabled:
                    bot_logger.debug(
                        "Command blocked — DJ role required",
                        user_id=ctx.author.id,
                        command=ctx.command.name if ctx.command else "unknown",
                        guild_id=ctx.guild.id if ctx.guild else None,
                    )
                await self._safe_send(ctx, view=err_design.dj_role_required(role_name))
            elif isinstance(error, commands.CheckFailure):
                print(f"\033[91m[ERROR] Check Failure\033[0m: {type(error).__name__} - Silently ignoring")
                if bot_logger.enabled:
                    bot_logger.debug(
                        "Check failure — silently ignored",
                        error_type=type(error).__name__,
                        guild_id=ctx.guild.id if ctx.guild else None,
                    )
                return
            else:
                print(f"\033[91m[ERROR] Unexpected Error\033[0m: {type(error).__name__}: {error}")
                traceback.print_exception(type(error), error, error.__traceback__)
                if bot_logger.enabled:
                    await bot_logger.async_error(
                        "Unexpected command error",
                        error_type=type(error).__name__,
                        error=str(error),
                        command=ctx.command.name if ctx.command else "unknown",
                        user_id=ctx.author.id,
                        guild_id=ctx.guild.id if ctx.guild else None,
                    )
                await self._safe_send(ctx, view=err_design.unexpected_error(str(error)))
        except Exception as exc:
            print(f"\033[91m[ERROR] Critical Error Handler Error\033[0m: {type(exc).__name__}: {exc}")
            traceback.print_exception(type(exc), exc, exc.__traceback__)
            if bot_logger.enabled:
                bot_logger.error(
                    "Critical — error inside on_command_error handler",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            try:
                await self._safe_send(ctx, view=err_design.critical_error())
            except Exception as e:
                print(f"\033[91m[ERROR] Critical Error Send Failed\033[0m: {e}")

async def setup(bot):
    _install_ctx_send_patch()
    async with _errorhandler_setup_lock:
        if bot.get_cog("ErrorHandler") is not None:
            return
        await bot.add_cog(ErrorHandler(bot))
