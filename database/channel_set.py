import os
import asyncpg


async def channel_set_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS player_channels (
                guild_id BIGINT NOT NULL,
                bot_id BIGINT NOT NULL DEFAULT 0,
                player_channel_id BIGINT,
                voice_channel_id BIGINT,
                PRIMARY KEY (guild_id, bot_id)
            )
        """)
        # Migration: add bot_id column if upgrading from single-bot schema
        col_exists = await conn.fetchval(
            "SELECT 1 FROM information_schema.columns WHERE table_name='player_channels' AND column_name='bot_id'"
        )
        if not col_exists:
            await conn.execute("ALTER TABLE player_channels ADD COLUMN bot_id BIGINT NOT NULL DEFAULT 0")
            await conn.execute("ALTER TABLE player_channels DROP CONSTRAINT IF EXISTS player_channels_pkey")
            await conn.execute("ALTER TABLE player_channels ADD PRIMARY KEY (guild_id, bot_id)")
    except Exception as e:
        print(f"[ERROR] Failed to setup player_channels table: {e}")
    finally:
        if conn:
            await conn.close()

