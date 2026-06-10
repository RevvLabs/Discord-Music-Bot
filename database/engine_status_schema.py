import os
import asyncpg

async def engine_status_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS engine_status (
                engine_id TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Initialize default engines if not present
        engines = [
            "jssearch", "spsearch", "ytmsearch", "ytsearch", 
            "scsearch", "dzsearch", "amsearch", "ytdl"
        ]
        for engine_id in engines:
            await conn.execute("""
                INSERT INTO engine_status (engine_id, enabled)
                VALUES ($1, TRUE)
                ON CONFLICT (engine_id) DO NOTHING
            """, engine_id)
            
    except Exception as e:
        print(f"[ERROR] Failed to setup engine_status table: {e}")
    finally:
        if conn:
            await conn.close()
