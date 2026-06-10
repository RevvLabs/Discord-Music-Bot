import os
import asyncpg


async def user_profile_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_source_stats (
                user_id BIGINT,
                source  TEXT,
                count   BIGINT DEFAULT 0,
                PRIMARY KEY (user_id, source)
            )
        """)
    except Exception as e:
        print(f"[ERROR] Failed to setup user_source_stats table: {e}")
    finally:
        if conn:
            await conn.close()
