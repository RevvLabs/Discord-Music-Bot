import os
import asyncpg


async def dj_role_database():
    """
    DJ role table — keyed by guild_id only (NO bot_id).
    Since every bot shares the same DATABASE_URL, a single row per guild means
    all bots in that guild use the same common DJ role.
    """
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        # Advisory lock serialises table creation across bots that boot at the
        # same time — avoids the concurrent CREATE race on pg_type catalog.
        await conn.execute("SELECT pg_advisory_lock(hashtext('dj_roles_init'))")
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS dj_roles (
                    guild_id  BIGINT PRIMARY KEY,
                    role_id   BIGINT NOT NULL
                )
            """)
        finally:
            await conn.execute("SELECT pg_advisory_unlock(hashtext('dj_roles_init'))")
    except asyncpg.exceptions.UniqueViolationError:
        # Another bot created the table at the same instant — harmless.
        pass
    except Exception as e:
        print(f"[ERROR] Failed to setup dj_roles table: {e}")
    finally:
        if conn:
            await conn.close()
