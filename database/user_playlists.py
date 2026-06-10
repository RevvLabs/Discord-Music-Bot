import os
import asyncpg


async def user_playlists_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
      
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_playlists (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT NOT NULL,
                name        TEXT NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, name)
            )
        """)
       
    except Exception as e:
        print(f"[ERROR] Failed to setup user_playlists table: {e}")
    finally:
        if conn:
            await conn.close()
