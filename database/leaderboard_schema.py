
import os
import asyncpg


async def leaderboard_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_counts (
                guild_id BIGINT,
                user_id BIGINT,
                count BIGINT DEFAULT 0,
                minutes FLOAT DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
    except Exception as e:
        print(f"[ERROR] Failed to setup user_counts table: {e}")
    finally:
        if conn:
            await conn.close()

