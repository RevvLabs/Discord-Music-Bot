import os
import asyncpg


async def temp_setup_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS temp_setup (
                guild_id    BIGINT NOT NULL,
                bot_id      BIGINT NOT NULL DEFAULT 0,
                text_channel_id BIGINT NOT NULL,
                category_id BIGINT NOT NULL,
                PRIMARY KEY (guild_id, bot_id)
            )
        """)
    except Exception as e:
        print(f"[ERROR] Failed to setup temp_setup table: {e}")
    finally:
        if conn:
            await conn.close()
