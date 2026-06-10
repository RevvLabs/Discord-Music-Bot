import os
import asyncpg


async def user_favorite_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_favorites (
                user_id BIGINT,
                track_url TEXT,
                track_title TEXT,
                PRIMARY KEY (user_id, track_url, track_title)
            )
        """)
    except Exception as e:
        print(f"[ERROR] Failed to setup user_favorites table: {e}")
    finally:
        if conn:
            await conn.close()




