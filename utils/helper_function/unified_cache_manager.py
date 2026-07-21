import asyncio
import asyncpg
import os
import json
from typing import Optional, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()

class UnifiedCacheManager:
    """
    A centralized cache manager for Discord bot data.
    Provides in-memory caching for prefixes, blacklist, favorites, channel settings, and maintenance checks.
    All caching functionality is consolidated in this single file to avoid confusion.
    """
    
    def __init__(self, cache_ttl: int = 300):  # 5 minutes default TTL
        # Prefix cache: (guild_id, bot_id) -> prefix
        self._prefix_cache: Dict[Tuple[int, int], str] = {}
        self._prefix_timestamps: Dict[Tuple[int, int], float] = {}
        
        # Blacklist cache: user_id -> bool (True if blacklisted)
        self._blacklist_cache: Dict[int, bool] = {}
        self._blacklist_timestamps: Dict[int, float] = {}
        
        # Maintenance cache: global state
        self._maintenance_cache: Optional[Tuple[bool, float]] = None  # (enabled, timestamp)

        # Per-command lock cache: command_name -> {reason: str}
        self._locked_commands_cache: Dict[str, dict] = {}
        self._locked_commands_cache_time: float = 0.0
        
        # User favorites cache: user_id -> List[Tuple[track_url, track_title]]
        self._favorites_cache: Dict[int, list] = {}
        self._favorites_timestamps: Dict[int, float] = {}
        
        # User engine cache: user_id -> engine_name
        self._user_engine_cache: Dict[int, str] = {}
        self._user_engine_timestamps: Dict[int, float] = {}
        
        # Channel set cache: (guild_id, bot_id) -> Dict[channel_data]
        self._channel_set_cache: Dict[Tuple[int, int], dict] = {}
        self._channel_set_timestamps: Dict[Tuple[int, int], float] = {}

        # Hide controls cache: (guild_id, bot_id) -> bool
        self._hide_controls_cache: Dict[Tuple[int, int], bool] = {}
        self._hide_controls_timestamps: Dict[Tuple[int, int], float] = {}
        
        # Engine status cache: engine_id -> bool
        self._engine_status_cache: Dict[str, bool] = {}
        self._engine_status_timestamps: Dict[str, float] = {}

        # DJ role cache: guild_id -> role_id (or None). Keyed by guild only —
        # the DJ role is common across all bots sharing this database.
        self._dj_role_cache: Dict[int, Optional[int]] = {}
        self._dj_role_timestamps: Dict[int, float] = {}

        # DJ command overrides cache: guild_id -> {command_name -> locked bool}
        self._dj_cmd_overrides_cache: Dict[int, Dict[str, bool]] = {}
        self._dj_cmd_overrides_timestamps: Dict[int, float] = {}

        # Temp setup cache: (guild_id, bot_id) -> Dict[text_channel_id, category_id] or None
        self._temp_setup_cache: Dict[Tuple[int, int], Optional[dict]] = {}
        self._temp_setup_timestamps: Dict[Tuple[int, int], float] = {}

        # Temp VC ownership cache: (guild_id, voice_channel_id) -> bot_id or None.
        # Very short TTL — ownership must stay fresh; writes invalidate the key.
        self._vc_assignment_cache: Dict[Tuple[int, int], Optional[int]] = {}
        self._vc_assignment_timestamps: Dict[Tuple[int, int], float] = {}
        self._vc_assignment_ttl = 3.0  # seconds

        self.cache_ttl = cache_ttl
        self._lock = asyncio.Lock()
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.default_prefix = os.getenv("PREFIX", "-")
        self.MAINTENANCE_FILE = "json_Data/maintenance_shared.json"
        self.LOCKED_COMMANDS_FILE = "json_Data/locked_commands_shared.json"
        
    # =============================================================================
    # PREFIX CACHING
    # =============================================================================
    
    async def get_prefix(self, guild_id: int, bot_id: int = 0) -> str:
        """
        Get prefix for a guild+bot pair. Returns cached value if fresh,
        otherwise fetches from database and caches the result.
        """
        if not guild_id:
            return self.default_prefix

        key = (guild_id, bot_id)
        async with self._lock:
            if await self._is_prefix_cache_valid(key):
                return self._prefix_cache[key]

            prefix = await self._fetch_prefix_from_database(guild_id, bot_id)
            self._prefix_cache[key] = prefix
            self._prefix_timestamps[key] = asyncio.get_event_loop().time()
            return prefix

    async def set_prefix(self, guild_id: int, bot_id: int = 0, prefix: str = '-') -> bool:
        """
        Set prefix for a guild+bot pair in both database and cache.
        """
        if not self.DATABASE_URL:
            print("[ERROR] DATABASE_URL environment variable is not set.")
            return False

        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                """
                INSERT INTO prefixes (guild_id, bot_id, prefix)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, bot_id) DO UPDATE SET prefix = EXCLUDED.prefix
                """,
                guild_id, bot_id, prefix
            )

            key = (guild_id, bot_id)
            async with self._lock:
                self._prefix_cache[key] = prefix
                self._prefix_timestamps[key] = asyncio.get_event_loop().time()

            return True

        except Exception as e:
            print(f"[ERROR] Failed to set prefix: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def invalidate_prefix_cache(self, guild_id: int, bot_id: int = 0) -> None:
        """Remove a specific guild+bot prefix from cache."""
        key = (guild_id, bot_id)
        async with self._lock:
            self._prefix_cache.pop(key, None)
            self._prefix_timestamps.pop(key, None)
    
    # =============================================================================
    # BLACKLIST CACHING
    # =============================================================================
    
    async def is_user_blacklisted(self, user_id: int) -> bool:
        """
        Check if user is blacklisted. Returns cached value if available and fresh,
        otherwise fetches from database and caches the result.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            bool: True if user is blacklisted, False otherwise
        """
        async with self._lock:
            # Check if we have a valid cached entry
            if await self._is_blacklist_cache_valid(user_id):
                return self._blacklist_cache[user_id]
            
            # Cache miss or expired, fetch from database
            is_blacklisted = await self._fetch_blacklist_from_database(user_id)
            self._blacklist_cache[user_id] = is_blacklisted
            self._blacklist_timestamps[user_id] = asyncio.get_event_loop().time()
            return is_blacklisted
    
    async def add_user_to_blacklist(self, user_id: int) -> bool:
        """
        Add user to blacklist in both database and cache.
        
        Args:
            user_id: Discord user ID to blacklist
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.DATABASE_URL:
            print("[ERROR] DATABASE_URL environment variable is not set.")
            return False
            
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "INSERT INTO blacklist (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING",
                user_id
            )
            
            # Update cache immediately
            async with self._lock:
                self._blacklist_cache[user_id] = True
                self._blacklist_timestamps[user_id] = asyncio.get_event_loop().time()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to add user to blacklist: {e}")
            return False
        finally:
            if conn:
                await conn.close()
    
    async def remove_user_from_blacklist(self, user_id: int) -> bool:
        """
        Remove user from blacklist in both database and cache.
        
        Args:
            user_id: Discord user ID to remove from blacklist
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.DATABASE_URL:
            print("[ERROR] DATABASE_URL environment variable is not set.")
            return False
            
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute("DELETE FROM blacklist WHERE user_id = $1", user_id)
            
            # Update cache immediately
            async with self._lock:
                self._blacklist_cache[user_id] = False
                self._blacklist_timestamps[user_id] = asyncio.get_event_loop().time()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to remove user from blacklist: {e}")
            return False
        finally:
            if conn:
                await conn.close()
    
    # =============================================================================
    # MAINTENANCE MODE CACHING
    # =============================================================================
    
    async def is_maintenance_mode_enabled(self) -> bool:
        """
        Check if maintenance mode is enabled. Uses file-based caching with TTL.
        
        Returns:
            bool: True if maintenance mode is enabled, False otherwise
        """
        async with self._lock:
            current_time = asyncio.get_event_loop().time()
            
            # Check if we have a valid cached entry
            if (self._maintenance_cache and 
                (current_time - self._maintenance_cache[1]) < self.cache_ttl):
                return self._maintenance_cache[0]
            
            # Cache miss or expired, check file
            is_enabled = await self._check_maintenance_file()
            self._maintenance_cache = (is_enabled, current_time)
            return is_enabled
    
    async def set_maintenance_mode(self, enabled: bool) -> bool:
        """
        Set maintenance mode and update cache immediately.
        
        Args:
            enabled: Whether to enable maintenance mode
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = {"enabled": "on" if enabled else "off"}
            
            if enabled:
                with open(self.MAINTENANCE_FILE, "w") as f:
                    json.dump(data, f)
            else:
                # Remove file if disabling maintenance
                if os.path.exists(self.MAINTENANCE_FILE):
                    os.remove(self.MAINTENANCE_FILE)
            
            # Update cache immediately
            async with self._lock:
                self._maintenance_cache = (enabled, asyncio.get_event_loop().time())
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to set maintenance mode: {e}")
            return False
    
    # =============================================================================
    # PER-COMMAND LOCK
    # =============================================================================

    async def _ensure_locked_commands_fresh(self) -> None:
        """Reload locked commands from file if cache is stale. Must be called inside self._lock."""
        current_time = asyncio.get_event_loop().time()
        if current_time - self._locked_commands_cache_time < self.cache_ttl:
            return
        try:
            if os.path.exists(self.LOCKED_COMMANDS_FILE):
                with open(self.LOCKED_COMMANDS_FILE, "r") as f:
                    self._locked_commands_cache = json.load(f)
            else:
                self._locked_commands_cache = {}
            self._locked_commands_cache_time = current_time
        except Exception as e:
            print(f"[ERROR] Failed to load locked commands file: {e}")

    async def is_command_locked(self, command_name: str) -> Optional[str]:
        """Returns the maintenance reason if the command is locked, else None."""
        async with self._lock:
            await self._ensure_locked_commands_fresh()
            entry = self._locked_commands_cache.get(command_name)
            return entry.get("reason", "") if entry else None

    async def set_command_lock(self, command_name: str, locked: bool, reason: str = "") -> bool:
        """Lock or unlock a specific command."""
        async with self._lock:
            await self._ensure_locked_commands_fresh()
            if locked:
                self._locked_commands_cache[command_name] = {"reason": reason}
            else:
                self._locked_commands_cache.pop(command_name, None)
            self._locked_commands_cache_time = asyncio.get_event_loop().time()
            try:
                os.makedirs("json_Data", exist_ok=True)
                with open(self.LOCKED_COMMANDS_FILE, "w") as f:
                    json.dump(self._locked_commands_cache, f, indent=2)
                return True
            except Exception as e:
                print(f"[ERROR] Failed to save locked commands file: {e}")
                return False

    async def get_locked_commands(self) -> Dict[str, dict]:
        """Return a snapshot of all currently locked commands."""
        async with self._lock:
            await self._ensure_locked_commands_fresh()
            return dict(self._locked_commands_cache)

    # =============================================================================
    # USER FAVORITES CACHING
    # =============================================================================
    
    async def get_user_favorites(self, user_id: int) -> list:
        """Get user's favorite tracks from cache or database."""
        async with self._lock:
            if await self._is_favorites_cache_valid(user_id):
                return self._favorites_cache[user_id]
            
            favorites = await self._fetch_favorites_from_database(user_id)
            self._favorites_cache[user_id] = favorites
            self._favorites_timestamps[user_id] = asyncio.get_event_loop().time()
            return favorites
    
    async def add_user_favorite(self, user_id: int, track_url: str, track_title: str) -> bool:
        """Add a favorite track for user."""
        if not self.DATABASE_URL:
            return False
            
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "INSERT INTO user_favorites (user_id, track_url, track_title) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                user_id, track_url, track_title
            )
            
            # Update cache
            async with self._lock:
                if user_id in self._favorites_cache:
                    self._favorites_cache[user_id].append((track_url, track_title))
                    self._favorites_timestamps[user_id] = asyncio.get_event_loop().time()
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to add favorite: {e}")
            return False
        finally:
            if conn:
                await conn.close()
    
    async def remove_user_favorite(self, user_id: int, track_url: str, track_title: str) -> bool:
        """Remove a favorite track for user."""
        if not self.DATABASE_URL:
            return False
            
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "DELETE FROM user_favorites WHERE user_id = $1 AND track_url = $2 AND track_title = $3",
                user_id, track_url, track_title
            )
            
            # Update cache
            async with self._lock:
                if user_id in self._favorites_cache:
                    self._favorites_cache[user_id] = [
                        fav for fav in self._favorites_cache[user_id] 
                        if fav != (track_url, track_title)
                    ]
                    self._favorites_timestamps[user_id] = asyncio.get_event_loop().time()
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to remove favorite: {e}")
            return False
        finally:
            if conn:
                await conn.close()
    
    # =============================================================================
    # USER ENGINE CACHING
    # =============================================================================
    
    async def get_user_engine(self, user_id: int) -> Optional[str]:
        """Get user's selected engine from cache or database."""
        async with self._lock:
            if await self._is_user_engine_cache_valid(user_id):
                return self._user_engine_cache[user_id]
            
            engine = await self._fetch_user_engine_from_database(user_id)
            self._user_engine_cache[user_id] = engine
            self._user_engine_timestamps[user_id] = asyncio.get_event_loop().time()
            return engine
    
    async def set_user_engine(self, user_id: int, engine: str) -> bool:
        """Set user's selected engine."""
        if not self.DATABASE_URL:
            return False
            
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            if engine is None:
                await conn.execute(
                    "DELETE FROM user_engine_selection WHERE user_id = $1",
                    user_id
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO user_engine_selection (user_id, engine)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id) DO UPDATE SET engine = EXCLUDED.engine
                    """,
                    user_id, engine
                )
            
            # Update cache
            async with self._lock:
                self._user_engine_cache[user_id] = engine
                self._user_engine_timestamps[user_id] = asyncio.get_event_loop().time()
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to set user engine: {e}")
            return False
        finally:
            if conn:
                await conn.close()
    
    # =============================================================================
    # ENGINE STATUS CACHING
    # =============================================================================
    
    async def is_engine_enabled(self, engine_id: str) -> bool:
        """Check if an engine is globally enabled."""
        async with self._lock:
            current_time = asyncio.get_event_loop().time()
            if engine_id in self._engine_status_cache:
                if (current_time - self._engine_status_timestamps.get(engine_id, 0)) < self.cache_ttl:
                    return self._engine_status_cache[engine_id]
            
            enabled = await self._fetch_engine_status_from_database(engine_id)
            self._engine_status_cache[engine_id] = enabled
            self._engine_status_timestamps[engine_id] = current_time
            return enabled

    async def set_engine_status(self, engine_id: str, enabled: bool) -> bool:
        """Set global enabled status for an engine."""
        if not self.DATABASE_URL:
            return False
            
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "UPDATE engine_status SET enabled = $1 WHERE engine_id = $2",
                enabled, engine_id
            )
            
            # Update cache
            async with self._lock:
                self._engine_status_cache[engine_id] = enabled
                self._engine_status_timestamps[engine_id] = asyncio.get_event_loop().time()
            
            if not enabled:
                # If disabling, shift users
                await self.shift_users_of_disabled_engine(engine_id)
                
            return True
        except Exception as e:
            print(f"[ERROR] Failed to set engine status: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def _fetch_engine_status_from_database(self, engine_id: str) -> bool:
        if not self.DATABASE_URL:
            return True
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            row = await conn.fetchrow("SELECT enabled FROM engine_status WHERE engine_id = $1", engine_id)
            return row["enabled"] if row else True
        except Exception as e:
            print(f"[ERROR] Failed to fetch engine status: {e}")
            return True
        finally:
            if conn:
                await conn.close()

    async def shift_users_of_disabled_engine(self, disabled_engine_id: str):
        """Shift all users from a disabled engine to a fallback."""
        if not self.DATABASE_URL:
            return
            
        # Determine fallback: ytsearch > dzsearch > ytmsearch
        fallback = "ytsearch" # 1st Priority
        if disabled_engine_id == "ytsearch" or not await self.is_engine_enabled("ytsearch"):
            fallback = "dzsearch" # 2nd Priority
            if disabled_engine_id == "dzsearch" or not await self.is_engine_enabled("dzsearch"):
                # Find any enabled engine
                engines = ["ytmsearch", "spsearch", "scsearch", "jssearch", "amsearch", "ytdl"]
                for eng in engines:
                    if eng != disabled_engine_id and await self.is_engine_enabled(eng):
                        fallback = eng
                        break
        
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            # Find users using the disabled engine
            users = await conn.fetch("SELECT user_id FROM user_engine_selection WHERE engine = $1", disabled_engine_id)
            
            if users:
                await conn.execute(
                    "UPDATE user_engine_selection SET engine = $1 WHERE engine = $2",
                    fallback, disabled_engine_id
                )
                
                # Invalidate/Update cache for these users
                async with self._lock:
                    for record in users:
                        user_id = record["user_id"]
                        self._user_engine_cache[user_id] = fallback
                        self._user_engine_timestamps[user_id] = asyncio.get_event_loop().time()
                        
        except Exception as e:
            print(f"[ERROR] Failed to shift users: {e}")
        finally:
            if conn:
                await conn.close()
    
    # =============================================================================
    # CHANNEL SET CACHING
    # =============================================================================
    
    async def get_channel_set_data(self, guild_id: int, bot_id: int = 0) -> Optional[dict]:
        """Get channel set data from cache or database."""
        key = (guild_id, bot_id)
        async with self._lock:
            if await self._is_channel_set_cache_valid(key):
                return self._channel_set_cache[key]

            channel_data = await self._fetch_channel_set_from_database(guild_id, bot_id)
            self._channel_set_cache[key] = channel_data
            self._channel_set_timestamps[key] = asyncio.get_event_loop().time()
            return channel_data

    async def delete_channel_set_data(self, guild_id: int, bot_id: int) -> bool:
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "DELETE FROM player_channels WHERE guild_id = $1 AND bot_id = $2",
                guild_id, bot_id
            )
            key = (guild_id, bot_id)
            async with self._lock:
                self._channel_set_cache[key] = None
                self._channel_set_timestamps[key] = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete channel set data: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def set_channel_set_data(self, guild_id: int, bot_id: int, player_channel_id: int, voice_channel_id: int) -> bool:
        """Set channel set data for guild."""
        if not self.DATABASE_URL:
            return False

        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                """
                INSERT INTO player_channels (guild_id, bot_id, player_channel_id, voice_channel_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, bot_id) DO UPDATE SET
                    player_channel_id = EXCLUDED.player_channel_id,
                    voice_channel_id = EXCLUDED.voice_channel_id
                """,
                guild_id, bot_id, player_channel_id, voice_channel_id
            )

            key = (guild_id, bot_id)
            async with self._lock:
                self._channel_set_cache[key] = {
                    "player_channel_id": player_channel_id,
                    "voice_channel_id": voice_channel_id
                }
                self._channel_set_timestamps[key] = asyncio.get_event_loop().time()

            return True
        except Exception as e:
            print(f"[ERROR] Failed to set channel set data: {e}")
            return False
        finally:
            if conn:
                await conn.close()
    
    # =============================================================================
    # TEMP SETUP CACHING
    # =============================================================================

    async def get_temp_setup_data(self, guild_id: int, bot_id: int = 0) -> Optional[dict]:
        key = (guild_id, bot_id)
        async with self._lock:
            if key in self._temp_setup_cache and key in self._temp_setup_timestamps:
                if (asyncio.get_event_loop().time() - self._temp_setup_timestamps[key]) < self.cache_ttl:
                    return self._temp_setup_cache[key]

            data = await self._fetch_temp_setup_from_database(guild_id, bot_id)
            self._temp_setup_cache[key] = data
            self._temp_setup_timestamps[key] = asyncio.get_event_loop().time()
            return data

    async def set_temp_setup_data(self, guild_id: int, bot_id: int, text_channel_id: int, category_id: int) -> bool:
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                """
                INSERT INTO temp_setup (guild_id, bot_id, text_channel_id, category_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, bot_id) DO UPDATE SET
                    text_channel_id = EXCLUDED.text_channel_id,
                    category_id = EXCLUDED.category_id
                """,
                guild_id, bot_id, text_channel_id, category_id
            )
            key = (guild_id, bot_id)
            async with self._lock:
                self._temp_setup_cache[key] = {"text_channel_id": text_channel_id, "category_id": category_id}
                self._temp_setup_timestamps[key] = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to set temp setup data: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def delete_temp_setup_data(self, guild_id: int, bot_id: int) -> bool:
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute("DELETE FROM temp_setup WHERE guild_id = $1 AND bot_id = $2", guild_id, bot_id)
            key = (guild_id, bot_id)
            async with self._lock:
                self._temp_setup_cache[key] = None
                self._temp_setup_timestamps[key] = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete temp setup data: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def _fetch_temp_setup_from_database(self, guild_id: int, bot_id: int = 0) -> Optional[dict]:
        if not self.DATABASE_URL:
            return None
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            row = await conn.fetchrow(
                "SELECT text_channel_id, category_id FROM temp_setup WHERE guild_id = $1 AND bot_id = $2",
                guild_id, bot_id
            )
            if row:
                return {"text_channel_id": row["text_channel_id"], "category_id": row["category_id"]}
            return None
        except Exception as e:
            print(f"[ERROR] Failed to fetch temp setup from database: {e}")
            return None
        finally:
            if conn:
                await conn.close()

    # =============================================================================
    # TEMP VC ASSIGNMENTS (no-prefix ownership for temp setup bots)
    # =============================================================================

    def _invalidate_vc_assignment(self, guild_id: int, voice_channel_id: int) -> None:
        key = (guild_id, voice_channel_id)
        self._vc_assignment_cache.pop(key, None)
        self._vc_assignment_timestamps.pop(key, None)

    async def get_vc_assignment(self, guild_id: int, voice_channel_id: int) -> Optional[int]:
        """Return the bot_id currently owning this VC, or None. Cached with a short TTL."""
        if not self.DATABASE_URL:
            return None
        key = (guild_id, voice_channel_id)
        async with self._lock:
            ts = self._vc_assignment_timestamps.get(key)
            if ts is not None and (asyncio.get_event_loop().time() - ts) < self._vc_assignment_ttl:
                return self._vc_assignment_cache.get(key)
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            row = await conn.fetchrow(
                "SELECT bot_id FROM temp_vc_assignments WHERE guild_id = $1 AND voice_channel_id = $2",
                guild_id, voice_channel_id
            )
            bot_id = row["bot_id"] if row else None
            async with self._lock:
                self._vc_assignment_cache[key] = bot_id
                self._vc_assignment_timestamps[key] = asyncio.get_event_loop().time()
            return bot_id
        except Exception as e:
            print(f"[ERROR] Failed to read vc assignment: {e}")
            return None
        finally:
            if conn:
                await conn.close()

    async def claim_vc_assignment(
        self, guild_id: int, voice_channel_id: int, bot_id: int, text_channel_id: int = None
    ) -> Optional[int]:
        """
        Atomically claim an unowned VC. Returns the bot_id that ends up owning it
        (mine if I won, the existing owner if it was already taken). Safe across
        the separate bot processes via the PK + ON CONFLICT DO NOTHING.
        """
        if not self.DATABASE_URL:
            return None
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            row = await conn.fetchrow(
                """
                INSERT INTO temp_vc_assignments (guild_id, voice_channel_id, bot_id, text_channel_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, voice_channel_id) DO NOTHING
                RETURNING bot_id
                """,
                guild_id, voice_channel_id, bot_id, text_channel_id
            )
            if row:
                owner = bot_id  # I won the insert
            else:
                existing = await conn.fetchrow(
                    "SELECT bot_id FROM temp_vc_assignments WHERE guild_id = $1 AND voice_channel_id = $2",
                    guild_id, voice_channel_id
                )
                owner = existing["bot_id"] if existing else None
            async with self._lock:
                self._invalidate_vc_assignment(guild_id, voice_channel_id)
            return owner
        except Exception as e:
            print(f"[ERROR] Failed to claim vc assignment: {e}")
            return None
        finally:
            if conn:
                await conn.close()

    async def steal_vc_assignment(
        self, guild_id: int, voice_channel_id: int, new_bot_id: int, expected_old_bot_id: int,
        text_channel_id: int = None,
    ) -> bool:
        """
        Atomically take over a stale assignment (old owner gone from the VC).
        Compare-and-swap on the old bot_id → exactly one winner. Returns True if I won.
        """
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            # Grace window: never steal a freshly-claimed row — the owner may
            # still be mid-connect (join takes ~1s and it isn't in vc.members yet).
            row = await conn.fetchrow(
                """
                UPDATE temp_vc_assignments
                SET bot_id = $3, text_channel_id = COALESCE($4, text_channel_id), assigned_at = now()
                WHERE guild_id = $1 AND voice_channel_id = $2 AND bot_id = $5
                  AND assigned_at < now() - interval '15 seconds'
                RETURNING bot_id
                """,
                guild_id, voice_channel_id, new_bot_id, text_channel_id, expected_old_bot_id
            )
            async with self._lock:
                self._invalidate_vc_assignment(guild_id, voice_channel_id)
            return bool(row)
        except Exception as e:
            print(f"[ERROR] Failed to steal vc assignment: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def delete_vc_assignment(self, guild_id: int, voice_channel_id: int, bot_id: int) -> bool:
        """Release a VC I own (scoped to bot_id = me, never touches another bot's row)."""
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "DELETE FROM temp_vc_assignments WHERE guild_id = $1 AND voice_channel_id = $2 AND bot_id = $3",
                guild_id, voice_channel_id, bot_id
            )
            async with self._lock:
                self._invalidate_vc_assignment(guild_id, voice_channel_id)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete vc assignment: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def get_bot_vc_assignments(self, guild_id: int, bot_id: int) -> list:
        """Return this bot's active temp VC ownerships in a guild as a list of
        {"voice_channel_id", "text_channel_id"}. Empty list if none / no DB.
        Uncached — used only on the mention greeting (a rare, per-message event)."""
        if not self.DATABASE_URL:
            return []
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            rows = await conn.fetch(
                "SELECT voice_channel_id, text_channel_id FROM temp_vc_assignments "
                "WHERE guild_id = $1 AND bot_id = $2",
                guild_id, bot_id
            )
            return [
                {"voice_channel_id": r["voice_channel_id"], "text_channel_id": r["text_channel_id"]}
                for r in rows
            ]
        except Exception as e:
            print(f"[ERROR] Failed to read bot vc assignments: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def delete_bot_assignments(self, guild_id: int, bot_id: int) -> bool:
        """Release every VC I own in a guild (config cleared / guild left / restart prune)."""
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "DELETE FROM temp_vc_assignments WHERE guild_id = $1 AND bot_id = $2",
                guild_id, bot_id
            )
            async with self._lock:
                # Clear any cached entries for this guild (cheap — small dict).
                for key in [k for k in self._vc_assignment_cache if k[0] == guild_id]:
                    self._invalidate_vc_assignment(*key)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete bot assignments: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def delete_all_bot_assignments(self, bot_id: int) -> bool:
        """Release every VC I own across all guilds (called on startup — I hold none yet)."""
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute("DELETE FROM temp_vc_assignments WHERE bot_id = $1", bot_id)
            async with self._lock:
                self._vc_assignment_cache.clear()
                self._vc_assignment_timestamps.clear()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete all bot assignments: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def get_temp_setup_bot_ids(self, guild_id: int) -> list:
        """All temp-setup bot ids configured for a guild (for the no-bot-available notifier)."""
        if not self.DATABASE_URL:
            return []
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            rows = await conn.fetch(
                "SELECT DISTINCT bot_id FROM temp_setup WHERE guild_id = $1", guild_id
            )
            return [r["bot_id"] for r in rows]
        except Exception as e:
            print(f"[ERROR] Failed to read temp setup bot ids: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    # =============================================================================
    # HIDE CONTROLS CACHING
    # =============================================================================
    
    async def is_hide_controls_enabled(self, guild_id: int, bot_id: int = 0) -> bool:
        """Check if hide controls is enabled for guild."""
        key = (guild_id, bot_id)
        async with self._lock:
            if await self._is_hide_controls_cache_valid(key):
                return self._hide_controls_cache[key]

            is_enabled = await self._fetch_hide_controls_from_database(guild_id, bot_id)
            self._hide_controls_cache[key] = is_enabled
            self._hide_controls_timestamps[key] = asyncio.get_event_loop().time()
            return is_enabled

    async def set_hide_controls(self, guild_id: int, bot_id: int, enabled: bool) -> bool:
        """Set hide controls for guild."""
        if not self.DATABASE_URL:
            return False

        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                """
                INSERT INTO guild_controls (guild_id, bot_id, controls_hidden)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, bot_id) DO UPDATE SET controls_hidden = EXCLUDED.controls_hidden
                """,
                guild_id, bot_id, enabled
            )

            key = (guild_id, bot_id)
            async with self._lock:
                self._hide_controls_cache[key] = enabled
                self._hide_controls_timestamps[key] = asyncio.get_event_loop().time()

            return True
        except Exception as e:
            print(f"[ERROR] Failed to set hide controls: {e}")
            return False
        finally:
            if conn:
                await conn.close()
    
    # =============================================================================
    # DJ ROLE CACHING  (keyed by guild_id only — common across all bots)
    # =============================================================================

    async def get_dj_role(self, guild_id: int) -> Optional[int]:
        """Return the configured DJ role_id for a guild, or None if unset."""
        async with self._lock:
            current_time = asyncio.get_event_loop().time()
            if guild_id in self._dj_role_cache and (current_time - self._dj_role_timestamps.get(guild_id, 0)) < self.cache_ttl:
                return self._dj_role_cache[guild_id]

        role_id = await self._fetch_dj_role_from_database(guild_id)
        async with self._lock:
            self._dj_role_cache[guild_id] = role_id
            self._dj_role_timestamps[guild_id] = asyncio.get_event_loop().time()
        return role_id

    async def _fetch_dj_role_from_database(self, guild_id: int) -> Optional[int]:
        if not self.DATABASE_URL:
            return None
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            row = await conn.fetchrow("SELECT role_id FROM dj_roles WHERE guild_id = $1", guild_id)
            return row["role_id"] if row else None
        except Exception as e:
            print(f"[ERROR] Failed to fetch DJ role: {e}")
            return None
        finally:
            if conn:
                await conn.close()

    async def set_dj_role(self, guild_id: int, role_id: int) -> bool:
        """Set (or replace) the DJ role for a guild."""
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                """
                INSERT INTO dj_roles (guild_id, role_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET role_id = EXCLUDED.role_id
                """,
                guild_id, role_id,
            )
            async with self._lock:
                self._dj_role_cache[guild_id] = role_id
                self._dj_role_timestamps[guild_id] = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to set DJ role: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def clear_dj_role(self, guild_id: int) -> bool:
        """Remove the DJ role configuration for a guild."""
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute("DELETE FROM dj_roles WHERE guild_id = $1", guild_id)
            async with self._lock:
                self._dj_role_cache[guild_id] = None
                self._dj_role_timestamps[guild_id] = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to clear DJ role: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    # =============================================================================
    # DJ COMMAND OVERRIDES CACHING  (per-guild command lock settings)
    # =============================================================================

    async def get_command_dj_overrides(self, guild_id: int) -> Dict[str, bool]:
        """Return {command_name: locked} overrides for a guild (empty = all defaults)."""
        async with self._lock:
            current_time = asyncio.get_event_loop().time()
            if guild_id in self._dj_cmd_overrides_cache and (
                current_time - self._dj_cmd_overrides_timestamps.get(guild_id, 0)
            ) < self.cache_ttl:
                return dict(self._dj_cmd_overrides_cache[guild_id])

        overrides = await self._fetch_command_dj_overrides_from_db(guild_id)
        async with self._lock:
            self._dj_cmd_overrides_cache[guild_id] = overrides
            self._dj_cmd_overrides_timestamps[guild_id] = asyncio.get_event_loop().time()
        return dict(overrides)

    async def _fetch_command_dj_overrides_from_db(self, guild_id: int) -> Dict[str, bool]:
        if not self.DATABASE_URL:
            return {}
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            rows = await conn.fetch(
                "SELECT command_name, locked FROM dj_command_overrides WHERE guild_id = $1", guild_id
            )
            return {row["command_name"]: row["locked"] for row in rows}
        except Exception as e:
            print(f"[ERROR] Failed to fetch DJ command overrides: {e}")
            return {}
        finally:
            if conn:
                await conn.close()

    async def set_command_dj_lock(self, guild_id: int, command_name: str, locked: bool) -> bool:
        """Insert or update the DJ lock override for one command in a guild."""
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                """
                INSERT INTO dj_command_overrides (guild_id, command_name, locked)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, command_name) DO UPDATE SET locked = EXCLUDED.locked
                """,
                guild_id, command_name, locked,
            )
            async with self._lock:
                if guild_id not in self._dj_cmd_overrides_cache:
                    self._dj_cmd_overrides_cache[guild_id] = {}
                self._dj_cmd_overrides_cache[guild_id][command_name] = locked
                self._dj_cmd_overrides_timestamps[guild_id] = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to set DJ command lock: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def reset_command_dj_lock(self, guild_id: int, command_name: str) -> bool:
        """Remove the per-guild override, reverting to the coded default."""
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "DELETE FROM dj_command_overrides WHERE guild_id = $1 AND command_name = $2",
                guild_id, command_name,
            )
            async with self._lock:
                if guild_id in self._dj_cmd_overrides_cache:
                    self._dj_cmd_overrides_cache[guild_id].pop(command_name, None)
                    self._dj_cmd_overrides_timestamps[guild_id] = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to reset DJ command lock: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def get_all_command_dj_overrides(self, guild_id: int) -> Dict[str, bool]:
        """Alias for get_command_dj_overrides — returns the full override map."""
        return await self.get_command_dj_overrides(guild_id)

    # =============================================================================
    # CACHE MANAGEMENT
    # =============================================================================

    async def preload_cache(self) -> None:
        """
        Preload all data from database into cache during bot startup.
        """
        if not self.DATABASE_URL:
            print("[ERROR] DATABASE_URL environment variable is not set.")
            return
            
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            current_time = asyncio.get_event_loop().time()
            
            async with self._lock:
                # Preload prefixes (keyed by (guild_id, bot_id) pair)
                prefix_rows = await conn.fetch("SELECT guild_id, bot_id, prefix FROM prefixes")
                for row in prefix_rows:
                    key = (row["guild_id"], row["bot_id"])
                    self._prefix_cache[key] = row["prefix"]
                    self._prefix_timestamps[key] = current_time
                
                # Preload blacklist
                blacklist_rows = await conn.fetch("SELECT user_id FROM blacklist")
                for row in blacklist_rows:
                    self._blacklist_cache[row["user_id"]] = True
                    self._blacklist_timestamps[row["user_id"]] = current_time

                # Preload user favorites
                favorites_rows = await conn.fetch("SELECT user_id, track_url, track_title FROM user_favorites")
                favorites_by_user = {}
                for row in favorites_rows:
                    user_id = row["user_id"]
                    if user_id not in favorites_by_user:
                        favorites_by_user[user_id] = []
                    favorites_by_user[user_id].append((row["track_url"], row["track_title"]))
                for user_id, favorites in favorites_by_user.items():
                    self._favorites_cache[user_id] = favorites
                    self._favorites_timestamps[user_id] = current_time
                
                # Preload user engine selection
                engine_rows = await conn.fetch("SELECT user_id, engine FROM user_engine_selection")
                for row in engine_rows:
                    self._user_engine_cache[row["user_id"]] = row["engine"]
                    self._user_engine_timestamps[row["user_id"]] = current_time
                
                # Preload channel set data
                channel_set_rows = await conn.fetch("SELECT guild_id, bot_id, player_channel_id, voice_channel_id FROM player_channels")
                for row in channel_set_rows:
                    key = (row["guild_id"], row["bot_id"])
                    self._channel_set_cache[key] = {
                        "player_channel_id": row["player_channel_id"],
                        "voice_channel_id": row["voice_channel_id"]
                    }
                    self._channel_set_timestamps[key] = current_time

                # Preload hide controls
                hide_controls_rows = await conn.fetch("SELECT guild_id, bot_id, controls_hidden FROM guild_controls")
                for row in hide_controls_rows:
                    key = (row["guild_id"], row["bot_id"])
                    self._hide_controls_cache[key] = row["controls_hidden"]
                    self._hide_controls_timestamps[key] = current_time

                # Preload temp setup
                temp_setup_rows = await conn.fetch("SELECT guild_id, bot_id, text_channel_id, category_id FROM temp_setup")
                for row in temp_setup_rows:
                    key = (row["guild_id"], row["bot_id"])
                    self._temp_setup_cache[key] = {
                        "text_channel_id": row["text_channel_id"],
                        "category_id": row["category_id"]
                    }
                    self._temp_setup_timestamps[key] = current_time

            print(f"[CACHE] Preloaded all tables: {len(prefix_rows)} prefixes, {len(blacklist_rows)} blacklisted users, {len(favorites_by_user)} users with favorites, {len(engine_rows)} user engines, {len(channel_set_rows)} channel sets, {len(hide_controls_rows)} hide controls, {len(temp_setup_rows)} temp setups \n")
            
        except Exception as e:
            print(f"[ERROR] Failed to preload unified cache: {e}")
        finally:
            if conn:
                await conn.close()
    
    async def clear_cache(self) -> None:
        """Clear all caches."""
        async with self._lock:
            self._prefix_cache.clear()
            self._prefix_timestamps.clear()
            self._blacklist_cache.clear()
            self._blacklist_timestamps.clear()
            self._maintenance_cache = None
            self._locked_commands_cache.clear()
            self._locked_commands_cache_time = 0.0
            self._favorites_cache.clear()
            self._favorites_timestamps.clear()
            self._user_engine_cache.clear()
            self._user_engine_timestamps.clear()
            self._channel_set_cache.clear()
            self._channel_set_timestamps.clear()
            self._hide_controls_cache.clear()
            self._hide_controls_timestamps.clear()
            self._dj_cmd_overrides_cache.clear()
            self._dj_cmd_overrides_timestamps.clear()
    
    async def clear_prefix_cache(self) -> None:
        """Clear only the prefix cache."""
        async with self._lock:
            self._prefix_cache.clear()
            self._prefix_timestamps.clear()
    
    async def clear_blacklist_cache(self) -> None:
        """Clear only the blacklist cache."""
        async with self._lock:
            self._blacklist_cache.clear()
            self._blacklist_timestamps.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Dict with cache statistics
        """
        return {
            "cached_prefixes": len(self._prefix_cache),
            "blacklisted_users": len(self._blacklist_cache),
            "cached_favorites": len(self._favorites_cache),
            "cached_user_engines": len(self._user_engine_cache),
            "cached_channel_sets": len(self._channel_set_cache),
            "cached_hide_controls": len(self._hide_controls_cache),
            "cache_ttl": self.cache_ttl,
            "maintenance_cached": self._maintenance_cache is not None
        }
    
    # =============================================================================
    # PRIVATE HELPER METHODS
    # =============================================================================
    
    async def _is_prefix_cache_valid(self, key: Tuple[int, int]) -> bool:
        """Check if prefix cached entry is still valid. key = (guild_id, bot_id)."""
        if key not in self._prefix_cache or key not in self._prefix_timestamps:
            return False

        current_time = asyncio.get_event_loop().time()
        cache_time = self._prefix_timestamps[key]
        return (current_time - cache_time) < self.cache_ttl
    
    async def _is_blacklist_cache_valid(self, user_id: int) -> bool:
        """Check if blacklist cached entry is still valid."""
        if user_id not in self._blacklist_cache or user_id not in self._blacklist_timestamps:
            return False
            
        current_time = asyncio.get_event_loop().time()
        cache_time = self._blacklist_timestamps[user_id]
        return (current_time - cache_time) < self.cache_ttl
    
    async def _fetch_prefix_from_database(self, guild_id: int, bot_id: int = 0) -> str:
        """Fetch prefix from database for a specific guild+bot pair."""
        if not self.DATABASE_URL:
            return self.default_prefix

        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            row = await conn.fetchrow(
                "SELECT prefix FROM prefixes WHERE guild_id = $1 AND bot_id = $2",
                guild_id, bot_id
            )
            return row["prefix"] if row else self.default_prefix

        except Exception as e:
            print(f"[ERROR] Failed to fetch prefix from database: {e}")
            return self.default_prefix
        finally:
            if conn:
                await conn.close()
    
    async def _fetch_blacklist_from_database(self, user_id: int) -> bool:
        """Fetch blacklist status from database."""
        if not self.DATABASE_URL:
            return False
            
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            row = await conn.fetchrow("SELECT 1 FROM blacklist WHERE user_id = $1", user_id)
            return row is not None
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch blacklist from database: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def _check_maintenance_file(self) -> bool:
        """Check maintenance file status."""
        try:
            if not os.path.exists(self.MAINTENANCE_FILE):
                return False
                
            with open(self.MAINTENANCE_FILE, "r") as f:
                data = json.load(f)
            return data.get("enabled") == "on"
            
        except Exception as e:
            print(f"[ERROR] Failed to check maintenance file: {e}")
            return False
    
    # =============================================================================
    # ADDITIONAL CACHE VALIDATION METHODS
    # =============================================================================
    
    async def _is_favorites_cache_valid(self, user_id: int) -> bool:
        """Check if favorites cached entry is still valid."""
        if user_id not in self._favorites_cache or user_id not in self._favorites_timestamps:
            return False
        current_time = asyncio.get_event_loop().time()
        cache_time = self._favorites_timestamps[user_id]
        return (current_time - cache_time) < self.cache_ttl
    
    async def _is_user_engine_cache_valid(self, user_id: int) -> bool:
        """Check if user engine cached entry is still valid."""
        if user_id not in self._user_engine_cache or user_id not in self._user_engine_timestamps:
            return False
        current_time = asyncio.get_event_loop().time()
        cache_time = self._user_engine_timestamps[user_id]
        return (current_time - cache_time) < self.cache_ttl
    
    async def _is_channel_set_cache_valid(self, key: Tuple[int, int]) -> bool:
        """Check if channel set cached entry is still valid. key = (guild_id, bot_id)."""
        if key not in self._channel_set_cache or key not in self._channel_set_timestamps:
            return False
        current_time = asyncio.get_event_loop().time()
        cache_time = self._channel_set_timestamps[key]
        return (current_time - cache_time) < self.cache_ttl

    async def _is_hide_controls_cache_valid(self, key: Tuple[int, int]) -> bool:
        """Check if hide controls cached entry is still valid. key = (guild_id, bot_id)."""
        if key not in self._hide_controls_cache or key not in self._hide_controls_timestamps:
            return False
        current_time = asyncio.get_event_loop().time()
        cache_time = self._hide_controls_timestamps[key]
        return (current_time - cache_time) < self.cache_ttl
    
    # =============================================================================
    # ADDITIONAL DATABASE FETCH METHODS
    # =============================================================================
    
    async def _fetch_favorites_from_database(self, user_id: int) -> list:
        """Fetch user favorites from database."""
        if not self.DATABASE_URL:
            return []
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            rows = await conn.fetch("SELECT track_url, track_title FROM user_favorites WHERE user_id = $1", user_id)
            return [(row["track_url"], row["track_title"]) for row in rows]
        except Exception as e:
            print(f"[ERROR] Failed to fetch favorites from database: {e}")
            return []
        finally:
            if conn:
                await conn.close()
    
    async def _fetch_user_engine_from_database(self, user_id: int) -> Optional[str]:
        """Fetch user engine from database."""
        if not self.DATABASE_URL:
            return None
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            row = await conn.fetchrow("SELECT engine FROM user_engine_selection WHERE user_id = $1", user_id)
            return row["engine"] if row else None
        except Exception as e:
            print(f"[ERROR] Failed to fetch user engine from database: {e}")
            return None
        finally:
            if conn:
                await conn.close()
    
    async def _fetch_channel_set_from_database(self, guild_id: int, bot_id: int = 0) -> Optional[dict]:
        """Fetch channel set from database."""
        if not self.DATABASE_URL:
            return None
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            row = await conn.fetchrow(
                "SELECT player_channel_id, voice_channel_id FROM player_channels WHERE guild_id = $1 AND bot_id = $2",
                guild_id, bot_id
            )
            if row:
                return {
                    "player_channel_id": row["player_channel_id"],
                    "voice_channel_id": row["voice_channel_id"]
                }
            return None
        except Exception as e:
            print(f"[ERROR] Failed to fetch channel set from database: {e}")
            return None
        finally:
            if conn:
                await conn.close()

    async def _fetch_hide_controls_from_database(self, guild_id: int, bot_id: int = 0) -> bool:
        """Fetch hide controls from database."""
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            row = await conn.fetchrow(
                "SELECT controls_hidden FROM guild_controls WHERE guild_id = $1 AND bot_id = $2",
                guild_id, bot_id
            )
            return row["controls_hidden"] if row else False
        except Exception as e:
            print(f"[ERROR] Failed to fetch hide controls from database: {e}")
            return False
        finally:
            if conn:
                await conn.close()
    
    # =============================================================================
    # USER PLAYLISTS CACHING
    # =============================================================================

    _PLAYLIST_MAX_SONGS = 100

    def _init_playlist_caches(self):
        if not hasattr(self, "_playlists_cache"):
            self._playlists_cache: Dict[int, list] = {}
            self._playlists_timestamps: Dict[int, float] = {}
        if not hasattr(self, "_playlist_songs_cache"):
            self._playlist_songs_cache: Dict[int, list] = {}
            self._playlist_songs_timestamps: Dict[int, float] = {}

    async def get_user_playlists(self, user_id: int) -> list:
        """Return list of (id, name, song_count) tuples for the user, cached."""
        async with self._lock:
            self._init_playlist_caches()
            current_time = asyncio.get_event_loop().time()
            if user_id in self._playlists_cache and (current_time - self._playlists_timestamps.get(user_id, 0)) < self.cache_ttl:
                return self._playlists_cache[user_id]

        rows = await self._fetch_playlists_from_database(user_id)
        async with self._lock:
            self._playlists_cache[user_id] = rows
            self._playlists_timestamps[user_id] = asyncio.get_event_loop().time()
        return rows

    async def _fetch_playlists_from_database(self, user_id: int) -> list:
        if not self.DATABASE_URL:
            return []
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            rows = await conn.fetch(
                """
                SELECT p.id, p.name, COALESCE(COUNT(s.id), 0) AS song_count
                FROM user_playlists p
                LEFT JOIN user_playlist_songs s ON s.playlist_id = p.id
                WHERE p.user_id = $1
                GROUP BY p.id, p.name, p.created_at
                ORDER BY p.created_at ASC
                """,
                user_id,
            )
            return [(r["id"], r["name"], r["song_count"]) for r in rows]
        except Exception as e:
            print(f"[ERROR] Failed to fetch user playlists: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def create_user_playlist(self, user_id: int, name: str) -> bool:
        """Create a new named playlist with no songs. Returns False if name already exists."""
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "INSERT INTO user_playlists (user_id, name) VALUES ($1, $2)",
                user_id, name,
            )
            async with self._lock:
                self._init_playlist_caches()
                self._playlists_cache.pop(user_id, None)
            return True
        except asyncpg.UniqueViolationError:
            return False
        except Exception as e:
            print(f"[ERROR] Failed to create user playlist: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    async def remove_user_playlist(self, user_id: int, playlist_id: int) -> bool:
        """Delete a playlist and all its songs (cascade)."""
        if not self.DATABASE_URL:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "DELETE FROM user_playlists WHERE id = $1 AND user_id = $2",
                playlist_id, user_id,
            )
            async with self._lock:
                self._init_playlist_caches()
                self._playlists_cache.pop(user_id, None)
                self._playlist_songs_cache.pop(playlist_id, None)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to remove user playlist: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    # ── Playlist songs ────────────────────────────────────────────────────────

    async def get_playlist_songs(self, playlist_id: int) -> list:
        """Return list of (id, title, author) tuples for a playlist, cached."""
        async with self._lock:
            self._init_playlist_caches()
            current_time = asyncio.get_event_loop().time()
            if playlist_id in self._playlist_songs_cache and (current_time - self._playlist_songs_timestamps.get(playlist_id, 0)) < self.cache_ttl:
                return self._playlist_songs_cache[playlist_id]

        rows = await self._fetch_playlist_songs_from_database(playlist_id)
        async with self._lock:
            self._playlist_songs_cache[playlist_id] = rows
            self._playlist_songs_timestamps[playlist_id] = asyncio.get_event_loop().time()
        return rows

    async def _fetch_playlist_songs_from_database(self, playlist_id: int) -> list:
        if not self.DATABASE_URL:
            return []
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            rows = await conn.fetch(
                "SELECT id, track_title, track_author FROM user_playlist_songs WHERE playlist_id = $1 ORDER BY added_at ASC",
                playlist_id,
            )
            return [(r["id"], r["track_title"], r["track_author"]) for r in rows]
        except Exception as e:
            print(f"[ERROR] Failed to fetch playlist songs: {e}")
            return []
        finally:
            if conn:
                await conn.close()

    async def add_song_to_playlist(self, playlist_id: int, user_id: int, title: str, author: str) -> str:
        """
        Add a song to a playlist. Returns:
          'ok'        — added successfully
          'duplicate' — song already in playlist
          'full'      — playlist has reached 100 songs
          'error'     — unexpected error
        """
        if not self.DATABASE_URL:
            return "error"
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_playlist_songs WHERE playlist_id = $1",
                playlist_id,
            )
            if count >= self._PLAYLIST_MAX_SONGS:
                return "full"
            await conn.execute(
                """
                INSERT INTO user_playlist_songs (playlist_id, user_id, track_title, track_author)
                VALUES ($1, $2, $3, $4)
                """,
                playlist_id, user_id, title, author,
            )
            async with self._lock:
                self._init_playlist_caches()
                self._playlist_songs_cache.pop(playlist_id, None)
                self._playlists_cache.pop(user_id, None)
            return "ok"
        except asyncpg.UniqueViolationError:
            return "duplicate"
        except Exception as e:
            print(f"[ERROR] Failed to add song to playlist: {e}")
            return "error"
        finally:
            if conn:
                await conn.close()

    async def remove_songs_from_playlist(self, playlist_id: int, user_id: int, song_ids: list) -> bool:
        """Remove a batch of songs from a playlist by their IDs."""
        if not self.DATABASE_URL or not song_ids:
            return False
        conn = None
        try:
            conn = await asyncpg.connect(self.DATABASE_URL)
            await conn.execute(
                "DELETE FROM user_playlist_songs WHERE playlist_id = $1 AND id = ANY($2::int[])",
                playlist_id, song_ids,
            )
            async with self._lock:
                self._init_playlist_caches()
                self._playlist_songs_cache.pop(playlist_id, None)
                self._playlists_cache.pop(user_id, None)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to remove songs from playlist: {e}")
            return False
        finally:
            if conn:
                await conn.close()

    def invalidate_user_playlists_cache(self, user_id: int) -> None:
        """Force next read to hit the database."""
        if hasattr(self, "_playlists_cache"):
            self._playlists_cache.pop(user_id, None)

# Global unified cache instance
unified_cache = UnifiedCacheManager()

# Backward compatibility aliases for existing code
prefix_cache = unified_cache
check_decorators_cache = unified_cache
