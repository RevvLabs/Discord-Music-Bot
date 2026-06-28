"""
Temp Setup — No-Prefix ownership resolver
==========================================
Completely separate from the normal `/setup` no-prefix system (which lives in
get_prefix._no_prefix_active and reads channel_set). This module only ever
activates for a bot that has a *temp_setup* row for the guild.

Because every bot is its own process, there is no central router: each temp bot
runs `resolve()` independently on the same message and decides "is this VC mine?"
using the shared `temp_vc_assignments` table as the single source of truth.

resolve() returns:
    ""   -> this bot owns/just-claimed the VC  → caller enables the empty prefix
    None -> not this bot's VC (or not a temp context) → caller uses normal prefix
"""
from __future__ import annotations

import asyncio
import discord

from utils.helper_function.unified_cache_manager import unified_cache
from utils.check_decorators.dj_checker import dj_check_member
from utils.helper_function.embed_layout import build_basic_layout
from utils.helper_function.auto_delete import schedule_delete

# Bare commands allowed to CLAIM a VC (and therefore join). Other no-prefix
# commands require an assignment to already exist.
_JOIN_COMMANDS = {"play", "p", "search", "join"}

# Per-(guild, vc) cooldown for the "all bots busy" notice, and strong refs to
# fire-and-forget notifier tasks (asyncio only keeps weak refs otherwise).
_notify_cooldown: dict[tuple[int, int], float] = {}
_pending_tasks: set[asyncio.Task] = set()
_NOTIFY_COOLDOWN = 10.0  # seconds


def _first_token(content: str) -> str:
    content = (content or "").strip()
    return content.split()[0].lower() if content else ""


async def decide_ownership(bot, guild, vc, is_join: bool, text_channel_id: int = None) -> str:
    """
    Pure VC-ownership decision for THIS bot. Returns 'mine' or 'not_mine'.
    May atomically claim an unowned VC or steal a stale one. Shared by the
    no-prefix resolver AND the prefix-command gate (enforce_setup) so a single
    bot owns a VC regardless of how the command was invoked.
    """
    me = bot.user.id if bot.user else 0
    owner = await unified_cache.get_vc_assignment(guild.id, vc.id)
    # Another bot physically in the VC = already served; never pile a 2nd bot in.
    other_bot_in_vc = any(m.bot and m.id != me for m in vc.members)

    if owner == me:
        return "mine"

    if owner is not None and owner != me:
        owner_present = any(m.id == owner for m in vc.members)
        if owner_present:
            return "not_mine"
        # Stale (owner gone past the grace window) — take over only on a join
        # command, if I'm free, and only if no other bot occupies the VC.
        if is_join and guild.voice_client is None and not other_bot_in_vc:
            won = await unified_cache.steal_vc_assignment(
                guild.id, vc.id, me, owner, text_channel_id=text_channel_id
            )
            if won:
                return "mine"
        return "not_mine"

    # Unowned
    if not is_join:
        return "not_mine"            # non-join commands can't claim a VC
    if other_bot_in_vc:
        return "not_mine"            # a bot is already here — don't join on top
    if guild.voice_client is not None:
        return "not_mine"            # I'm busy in another VC in this guild
    owner_now = await unified_cache.claim_vc_assignment(
        guild.id, vc.id, me, text_channel_id=text_channel_id
    )
    return "mine" if owner_now == me else "not_mine"


async def resolve(bot, message: discord.Message) -> str | None:
    """Decide whether THIS bot should handle a no-prefix command for this message."""
    try:
        guild = message.guild
        me = bot.user.id if bot.user else 0

        # 1. Only temp-setup bots. Text channel isn't mandatory — accept any
        #    channel inside the temp category (VC's own chat or any category
        #    text channel). The bot is always bound to the category.
        temp_data = await unified_cache.get_temp_setup_data(guild.id, me)
        if not temp_data:
            return None
        text_channel_id = temp_data["text_channel_id"]
        category_id = temp_data["category_id"]
        if getattr(message.channel, "category_id", None) != category_id:
            return None

        # 2. Author must be in a VC inside the configured category.
        author_voice = getattr(message.author, "voice", None)
        if not author_voice or not author_voice.channel:
            return None
        vc = author_voice.channel
        if vc.category_id != category_id:
            return None

        # 3. DJ check (no-op unless a DJ role is configured) — mirrors normal no-prefix.
        allowed, _ = await dj_check_member(message.author, guild)
        if not allowed:
            return None

        is_join = _first_token(message.content) in _JOIN_COMMANDS
        status = await decide_ownership(bot, guild, vc, is_join, text_channel_id=text_channel_id)
        if status == "mine":
            return ""

        # Not mine: only consider a "no bot available" notice when nobody is
        # serving this VC (no other bot physically present).
        if not any(m.bot and m.id != me for m in vc.members):
            _maybe_spawn_notifier(bot, message, vc, is_join)
        return None
    except Exception:
        return None


def _maybe_spawn_notifier(bot, message, vc, is_join: bool) -> None:
    """Fire-and-forget the 'all bots busy' check (dedups internally)."""
    if not is_join:
        return
    task = asyncio.create_task(_maybe_notify_no_bot(bot, message, vc))
    _pending_tasks.add(task)
    task.add_done_callback(_pending_tasks.discard)


async def _maybe_notify_no_bot(bot, message: discord.Message, vc) -> None:
    """
    Sent by exactly ONE bot (the lowest temp bot id for the guild). After a short
    grace period, if the VC is still unowned, no free bot took it → notify once.
    """
    try:
        guild = message.guild
        me = bot.user.id if bot.user else 0

        bot_ids = await unified_cache.get_temp_setup_bot_ids(guild.id)
        if not bot_ids or me != min(bot_ids):
            return  # not the designated responder

        key = (guild.id, vc.id)
        now = asyncio.get_event_loop().time()
        last = _notify_cooldown.get(key, 0.0)
        if now - last < _NOTIFY_COOLDOWN:
            return
        _notify_cooldown[key] = now

        # Give any free bot a moment to win the claim.
        await asyncio.sleep(1.5)
        if await unified_cache.get_vc_assignment(guild.id, vc.id) is not None:
            return  # a bot took it — no notice needed

        try:
            schedule_delete(await message.channel.send(
                view=build_basic_layout(
                    title="All music bots are busy",
                    description=(
                        f"Every available music bot is already playing in another voice channel.\n\n"
                        f"--- \nPlease try again once one is free, or use a prefix command."
                    ),
                )
            ))
        except Exception:
            pass
    except Exception:
        pass
