import os
import asyncpg


async def user_playlist_songs_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        return
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_playlist_songs (
                id           SERIAL PRIMARY KEY,
                playlist_id  INT NOT NULL,
                user_id      BIGINT NOT NULL,
                track_title  TEXT NOT NULL,
                track_author TEXT NOT NULL DEFAULT '',
                added_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (playlist_id, track_title, track_author),
                FOREIGN KEY (playlist_id) REFERENCES user_playlists(id) ON DELETE CASCADE
            )
        """)
    except Exception as e:
        print(f"[ERROR] Failed to setup user_playlist_songs table: {e}")
    finally:
        if conn:
            await conn.close()
