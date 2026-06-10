import os
import asyncpg


async def prefix_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create table with new composite PK schema (only if it doesn't exist yet)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prefixes (
                guild_id BIGINT NOT NULL,
                bot_id   BIGINT NOT NULL DEFAULT 0,
                prefix   TEXT DEFAULT '-',
                PRIMARY KEY (guild_id, bot_id)
            )
        """)

        # Migrate existing tables that still have the old single-column PK (no bot_id)
        col_exists = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'prefixes' AND column_name = 'bot_id'
        """)
        if not col_exists:
            await conn.execute(
                "ALTER TABLE prefixes ADD COLUMN IF NOT EXISTS bot_id BIGINT NOT NULL DEFAULT 0"
            )
            await conn.execute(
                "ALTER TABLE prefixes DROP CONSTRAINT IF EXISTS prefixes_pkey"
            )
            await conn.execute(
                "ALTER TABLE prefixes ADD PRIMARY KEY (guild_id, bot_id)"
            )

    except Exception as e:
        print(f"[ERROR] Failed to setup prefixes table: {e}")
    finally:
        if conn:
            await conn.close()
