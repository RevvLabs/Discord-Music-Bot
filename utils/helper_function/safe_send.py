"""
safe_send — resilient message / file sending
=============================================
Centralised send helpers that survive Discord-side edge cases the bot can't
control. The big one this module exists for:

    403 Forbidden (error code: 400001)
    "Access to file uploads has been limited for this guild"

This is a *per-guild* flag Discord applies (spam / raid / verification state).
It blocks BOT-initiated file uploads — but interaction (slash) responses are
exempt. That asymmetry is exactly why a `/profile` works while a prefix /
no-prefix `profile` silently fails in the same channel.

`safe_send_file()` uploads a generated file and, if the upload is rejected for
ANY reason, posts a text/embed `fallback` instead — so users get their data
rather than silence. `safe_send()` is the same idea for non-file payloads.

Both helpers also tolerate the patched `Context.send`
(cogs/events/error_handel._ctx_send_safe), which swallows exceptions and
returns ``None`` on failure: a ``None`` result is treated as a failed send and
triggers the fallback path.
"""
from __future__ import annotations

import io
import traceback
from typing import Union

import discord

from utils.logger.mewzik_logger import bot_logger

# Discord JSON error code for a guild whose file uploads are restricted.
UPLOAD_LIMITED_CODE = 400001

FallbackType = Union[str, "discord.ui.LayoutView", discord.Embed, None]


def is_upload_limited(error: Exception) -> bool:
    """True if *error* is the per-guild 'file uploads limited' Forbidden."""
    return isinstance(error, discord.Forbidden) and getattr(error, "code", None) == UPLOAD_LIMITED_CODE


def _cmd_name(ctx) -> str:
    return ctx.command.name if getattr(ctx, "command", None) else "unknown"


def _guild_id(ctx):
    return getattr(getattr(ctx, "guild", None), "id", None)


def _fallback_kwargs(fallback: FallbackType) -> dict | None:
    """Map a fallback payload to ctx.send kwargs. None => no fallback."""
    if fallback is None:
        return None
    if isinstance(fallback, str):
        return {"content": fallback}
    if isinstance(fallback, discord.Embed):
        return {"embed": fallback}
    # discord.ui.LayoutView (or any View)
    return {"view": fallback}


async def _send_fallback(ctx, fallback: FallbackType, *, ephemeral=None, where: str = "safe_send"):
    fb = _fallback_kwargs(fallback)
    if fb is None:
        return None
    if ephemeral is not None:
        fb.setdefault("ephemeral", ephemeral)
    try:
        return await ctx.send(**fb)
    except Exception as e:
        bot_logger.error(f"{where} — fallback also failed", command=_cmd_name(ctx), error=repr(e))
        return None


async def safe_send(ctx, *, fallback: FallbackType = None, **kwargs):
    """
    ctx.send that survives failures.

    Returns the sent Message, or None. On any failure — an exception OR a None
    return from the patched Context.send — the `fallback` payload is sent with
    file/files stripped (an upload limit is the most common cause).
    """
    try:
        result = await ctx.send(**kwargs)
    except discord.Forbidden as e:
        result = None
        if is_upload_limited(e):
            bot_logger.warning("safe_send — uploads limited for guild", command=_cmd_name(ctx), guild_id=_guild_id(ctx))
        else:
            bot_logger.error("safe_send — forbidden", command=_cmd_name(ctx), error=repr(e))
    except Exception as e:
        result = None
        bot_logger.error("safe_send — send failed", command=_cmd_name(ctx), error=repr(e))

    if result is not None:
        return result
    return await _send_fallback(ctx, fallback, ephemeral=kwargs.get("ephemeral"), where="safe_send")


async def safe_send_file(
    ctx,
    *,
    data: Union[bytes, io.BytesIO],
    filename: str,
    fallback: FallbackType = None,
    **kwargs,
):
    """
    Upload a file, with automatic text fallback when the guild blocks uploads.

    `data`     raw bytes or a BytesIO. A FRESH discord.File is built from the
               underlying bytes, so the buffer is never double-consumed.
    `filename` attachment filename.
    `fallback` str / LayoutView / Embed posted if the upload can't go through.
    `kwargs`   extra ctx.send kwargs (content=, view=, ephemeral=, ...).

    Returns the sent Message, or None if even the fallback failed.
    """
    raw = data.getvalue() if isinstance(data, io.BytesIO) else data

    try:
        result = await ctx.send(file=discord.File(io.BytesIO(raw), filename=filename), **kwargs)
    except discord.Forbidden as e:
        result = None
        if is_upload_limited(e):
            bot_logger.warning(
                "safe_send_file — uploads limited for guild, using text fallback",
                command=_cmd_name(ctx), guild_id=_guild_id(ctx),
            )
        else:
            bot_logger.error("safe_send_file — forbidden", command=_cmd_name(ctx), error=repr(e))
    except Exception as e:
        result = None
        bot_logger.error(
            "safe_send_file — send failed", command=_cmd_name(ctx),
            error=repr(e), traceback=traceback.format_exc(),
        )

    if result is not None:
        return result

    if fallback is None:
        bot_logger.warning("safe_send_file — upload failed and no fallback provided", command=_cmd_name(ctx))
        return None
    return await _send_fallback(ctx, fallback, ephemeral=kwargs.get("ephemeral"), where="safe_send_file")
