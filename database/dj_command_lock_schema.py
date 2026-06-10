import os
import asyncpg


async def dj_command_lock_database():
    """
    Per-guild DJ command lock overrides.
    Presence of a row = explicit override; absence = use DEFAULT_DJ_LOCKED_COMMANDS in dj_checker.py.
    """
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("SELECT pg_advisory_lock(hashtext('dj_command_lock_init'))")
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS dj_command_overrides (
                    guild_id     BIGINT  NOT NULL,
                    command_name TEXT    NOT NULL,
                    locked       BOOLEAN NOT NULL,
                    PRIMARY KEY (guild_id, command_name)
                )
            """)
        finally:
            await conn.execute("SELECT pg_advisory_unlock(hashtext('dj_command_lock_init'))")
    except asyncpg.exceptions.UniqueViolationError:
        pass
    except Exception as e:
        print(f"[ERROR] Failed to setup dj_command_overrides table: {e}")
    finally:
        if conn:
            await conn.close()
