from dataclasses import dataclass, field
from typing import Dict, Optional, Set
import os

BOT_OWNER_IDS = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]


@dataclass
class SessionInfo:
    owner_id: int
    owner_name: str
    allowed_users: Set[int] = field(default_factory=set)


class SessionManager:
    """
    In-memory per-guild session lock.
    A "private" session means only the session owner (and admins/bot owners) can
    run music commands. Resets automatically when the owner leaves the voice channel.
    """

    def __init__(self):
        self._sessions: Dict[int, SessionInfo] = {}

    def lock(self, guild_id: int, owner_id: int, owner_name: str) -> None:
        self._sessions[guild_id] = SessionInfo(owner_id=owner_id, owner_name=owner_name)

    def unlock(self, guild_id: int) -> None:
        self._sessions.pop(guild_id, None)

    def is_locked(self, guild_id: int) -> bool:
        return guild_id in self._sessions

    def get_info(self, guild_id: int) -> Optional[SessionInfo]:
        return self._sessions.get(guild_id)

    def add_user(self, guild_id: int, user_id: int) -> bool:
        info = self._sessions.get(guild_id)
        if not info:
            return False
        info.allowed_users.add(user_id)
        return True

    def remove_user(self, guild_id: int, user_id: int) -> bool:
        info = self._sessions.get(guild_id)
        if not info:
            return False
        info.allowed_users.discard(user_id)
        return True

    def is_allowed(self, guild_id: int, member) -> bool:
        """True if member may use music commands in this guild."""
        info = self._sessions.get(guild_id)
        if info is None:
            return True

        if member.id == info.owner_id:
            return True

        if member.id in info.allowed_users:
            return True

        if member.id in BOT_OWNER_IDS:
            return True

        perms = getattr(member, "guild_permissions", None)
        if perms and (perms.administrator or perms.manage_guild):
            return True

        return False


# Singleton used across all modules
session_manager = SessionManager()
