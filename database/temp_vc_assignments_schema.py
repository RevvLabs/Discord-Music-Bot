import os
import asyncpg


async def temp_vc_assignments_database():
    """
    Per-voice-channel ownership for the Temp Setup no-prefix system.

    Each row = one VC currently owned by one temp bot. PK (guild_id,
    voice_channel_id) guarantees a single owner per VC; the atomic
    INSERT ... ON CONFLICT DO NOTHING is what makes leaderless contention
    safe across the separate bot processes.
    """
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS temp_vc_assignments (
                guild_id          BIGINT NOT NULL,
                voice_channel_id  BIGINT NOT NULL,
                bot_id            BIGINT NOT NULL,
                text_channel_id   BIGINT,
                assigned_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (guild_id, voice_channel_id)
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_temp_vc_assignments_bot
            ON temp_vc_assignments (guild_id, bot_id)
        """)
    except Exception as e:
        print(f"[ERROR] Failed to setup temp_vc_assignments table: {e}")
    finally:
        if conn:
            await conn.close()
