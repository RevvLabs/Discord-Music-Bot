import asyncio
from database.blacklist_schema import blacklist_database
from database.channel_set import channel_set_database
from database.hide_control_schema import hide_contols_schema
from database.leaderboard_schema import leaderboard_database
from database.prefix import prefix_database
from database.user_engine_schema import user_engine_database
from database.user_favorites import user_favorite_database
from database.engine_status_schema import engine_status_database
from database.user_playlists import user_playlists_database
from database.user_playlist_songs import user_playlist_songs_database
from database.user_profile_schema import user_profile_database
from database.dj_role_schema import dj_role_database
from database.dj_command_lock_schema import dj_command_lock_database
from database.temp_setup_schema import temp_setup_database
from utils.helper_function.unified_cache_manager import unified_cache
from utils.colours.colours import *

async def initialize_databases():
    try:
        db_funcs = [
            (channel_set_database, "channel_set_database"),
            (user_favorite_database, "user_favorite_database"),
            (leaderboard_database, "leaderboard_database"),
            (user_engine_database, "user_engine_database"),
            (hide_contols_schema, "hide_contols_schema"),
            (blacklist_database, "blacklist_database"),
            (prefix_database, "prefix_database"),
            (engine_status_database, "engine_status_database"),
            (user_playlists_database, "user_playlists_database"),
            (user_profile_database, "user_profile_database"),
            (dj_role_database, "dj_role_database"),
            (dj_command_lock_database, "dj_command_lock_database"),
            (temp_setup_database, "temp_setup_database"),
        ]

        # Tables with foreign keys that depend on a table above. These run
        # AFTER the concurrent batch so their parent table is guaranteed to exist.
        dependent_funcs = [
            (user_playlist_songs_database, "user_playlist_songs_database"),  # FK → user_playlists
        ]

        async def run_and_report(func, name):
            try:
                await func()
                return True, name
            except Exception as e:
                print(f"\033[91m[ERROR] Database Init Error\033[0m: Failed to initialize table in {name}: {e}")
                return False, name

        try:
            results = await asyncio.gather(
                *(run_and_report(func, name) for func, name in db_funcs)
            )
            # Create FK-dependent tables sequentially after their parents exist
            for func, name in dependent_funcs:
                results = (*results, await run_and_report(func, name))

            total = len(db_funcs) + len(dependent_funcs)
            success_count = sum(1 for ok, _ in results if ok)
            print(f"\n{NEON_BLUE}[DATABASE INIT]{RESET} {success_count}/{total} tables initialized successfully{RESET}\n")

            try:
                await unified_cache.preload_cache()
                print(f"{BRIGHT_GREEN}[CACHE INIT]{RESET} Unified cache preloaded successfully{RESET}\n")
            except Exception as e:
                print(f"\033[91m[ERROR] Cache Preload Error\033[0m: {e}\n")

        except Exception as e:
            print(f"\033[91m[ERROR] Database Gather Error\033[0m: {e}")
    except Exception as e:
        print(f"\033[91m[ERROR] Database Initialization General Error\033[0m: {e}")
