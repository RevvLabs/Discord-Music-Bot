import os
import asyncpg


async def hide_contols_schema():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_controls (
                guild_id BIGINT NOT NULL,
                bot_id BIGINT NOT NULL DEFAULT 0,
                controls_hidden BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (guild_id, bot_id)
            )
        """)
        # Migration: add bot_id column if upgrading from single-bot schema
        col_exists = await conn.fetchval(
            "SELECT 1 FROM information_schema.columns WHERE table_name='guild_controls' AND column_name='bot_id'"
        )
        if not col_exists:
            await conn.execute("ALTER TABLE guild_controls ADD COLUMN bot_id BIGINT NOT NULL DEFAULT 0")
            await conn.execute("ALTER TABLE guild_controls DROP CONSTRAINT IF EXISTS guild_controls_pkey")
            await conn.execute("ALTER TABLE guild_controls ADD PRIMARY KEY (guild_id, bot_id)")
    except Exception as e:
        print(f"[ERROR] Failed to setup guild_controls table: {e}")
    finally:
        if conn:
            await conn.close()


