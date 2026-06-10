
import os
import asyncpg


async def user_engine_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_engine_selection (
                user_id BIGINT PRIMARY KEY,
                engine TEXT
            )
        """)
    except Exception as e:
        print(f"[ERROR] Failed to setup user_engine_selection table: {e}")
    finally:
        if conn:
            await conn.close()

