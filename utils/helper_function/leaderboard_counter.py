
import asyncpg
import os
import asyncio
from dotenv import load_dotenv
from collections import defaultdict
from utils.logger.mewzik_logger import bot_logger

load_dotenv()

# Global connection pool and batch processing for leaderboard_counter
_pool = None
_batch_data = defaultdict(int)          # (guild_id, user_id) -> count
_batch_minutes_data = defaultdict(float) # (guild_id, user_id) -> minutes
_source_batch_data = defaultdict(int)   # (user_id, source) -> count
_batch_lock = asyncio.Lock()
_batch_size = 50  # Process in batches of 50
_batch_timeout = 5.0  # Process batch after 5 seconds if not full
_batch_task = None

async def _initialize_pool():
    """Initialize the connection pool."""
    global _pool, _batch_task
    if _pool is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if DATABASE_URL:
            if bot_logger.enabled:
                bot_logger.outgoing(
                    "Leaderboard — creating DB connection pool",
                    min_size=3,
                    max_size=10,
                )
            _pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=3,
                max_size=10,
                command_timeout=60
            )
            if bot_logger.enabled:
                bot_logger.incoming(
                    "Leaderboard — DB connection pool ready",
                )
            # Start batch processing task
            _batch_task = asyncio.create_task(_batch_processor())

async def _batch_processor():
    """Background task to process batches periodically."""
    while True:
        try:
            await asyncio.sleep(_batch_timeout)
            await _process_batch()
            await _process_source_batch()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in leaderboard batch processor: {e}")
            if bot_logger.enabled:
                bot_logger.error(
                    "Leaderboard batch processor error",
                    error=str(e),
                )

async def _process_batch():
    """Process the current batch of user_counts count+minutes updates."""
    global _pool, _batch_data, _batch_minutes_data
    if not _pool:
        return

    async with _batch_lock:
        if not _batch_data and not _batch_minutes_data:
            return

        batch_items = list(_batch_data.items())
        minutes_items = list(_batch_minutes_data.items())
        _batch_data.clear()
        _batch_minutes_data.clear()

    if not batch_items and not minutes_items:
        return

    if bot_logger.enabled:
        bot_logger.outgoing(
            "Leaderboard — flushing batch to DB",
            batch_size=len(batch_items),
            table="user_counts",
        )

    # Merge count and minutes by key
    all_keys = set(k for k, _ in batch_items) | set(k for k, _ in minutes_items)
    count_map = dict(batch_items)
    minutes_map = dict(minutes_items)

    try:
        with bot_logger.timer() as t:
            async with _pool.acquire() as conn:
                async with conn.transaction():
                    for key in all_keys:
                        guild_id, user_id = key
                        c = count_map.get(key, 0)
                        m = minutes_map.get(key, 0.0)
                        await conn.execute(
                            """
                            INSERT INTO user_counts (guild_id, user_id, count, minutes)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (guild_id, user_id)
                            DO UPDATE SET
                                count = user_counts.count + $3,
                                minutes = user_counts.minutes + $4
                            """,
                            guild_id, user_id, c, m
                        )

        print(f"Processed batch of {len(all_keys)} user_counts updates")
        if bot_logger.enabled:
            bot_logger.incoming(
                "Leaderboard — batch flushed",
                batch_size=len(all_keys),
                elapsed_ms=t.elapsed_ms,
            )

    except Exception as e:
        print(f"Error processing user_counts batch: {e}")
        if bot_logger.enabled:
            bot_logger.error(
                "Leaderboard — batch flush failed, re-queuing",
                batch_size=len(all_keys),
                error=str(e),
            )
        async with _batch_lock:
            for key, c in count_map.items():
                _batch_data[key] += c
            for key, m in minutes_map.items():
                _batch_minutes_data[key] += m

async def increment_user_count(guild_id, user_id, count=1, minutes=0.0):
    """Increment user play count and listening minutes."""
    global _pool, _batch_data, _batch_minutes_data

    if _pool is None:
        await _initialize_pool()

    if not _pool:
        if bot_logger.enabled:
            bot_logger.warning(
                "Leaderboard — pool unavailable, using direct DB connection",
                guild_id=guild_id,
                user_id=user_id,
            )
        DATABASE_URL = os.getenv("DATABASE_URL")
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                """
                INSERT INTO user_counts (guild_id, user_id, count, minutes)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, user_id)
                DO UPDATE SET
                    count = user_counts.count + $3,
                    minutes = user_counts.minutes + $4
                """,
                guild_id, user_id, count, float(minutes)
            )
        finally:
            await conn.close()
        return

    async with _batch_lock:
        key = (guild_id, user_id)
        _batch_data[key] += count
        _batch_minutes_data[key] += float(minutes)

        if bot_logger.enabled:
            bot_logger.debug(
                "Leaderboard — count queued in batch",
                guild_id=guild_id,
                user_id=user_id,
                count=count,
                minutes=minutes,
                batch_len=len(_batch_data),
            )

        if len(_batch_data) >= _batch_size:
            await _process_batch()


async def _process_source_batch():
    """Process the current batch of user_source_stats updates."""
    global _pool, _source_batch_data
    if not _pool:
        return

    async with _batch_lock:
        if not _source_batch_data:
            return
        batch_items = list(_source_batch_data.items())
        _source_batch_data.clear()

    if not batch_items:
        return

    try:
        async with _pool.acquire() as conn:
            async with conn.transaction():
                for (user_id, source), count in batch_items:
                    await conn.execute(
                        """
                        INSERT INTO user_source_stats (user_id, source, count)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id, source)
                        DO UPDATE SET count = user_source_stats.count + $3
                        """,
                        user_id, source, count
                    )
    except Exception as e:
        print(f"Error processing user_source_stats batch: {e}")
        async with _batch_lock:
            for (user_id, source), count in batch_items:
                _source_batch_data[(user_id, source)] += count


async def increment_user_source(user_id: int, source: str):
    """Track which source a user played a song from."""
    global _pool, _source_batch_data

    if _pool is None:
        await _initialize_pool()

    if not _pool:
        DATABASE_URL = os.getenv("DATABASE_URL")
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                """
                INSERT INTO user_source_stats (user_id, source, count)
                VALUES ($1, $2, 1)
                ON CONFLICT (user_id, source)
                DO UPDATE SET count = user_source_stats.count + 1
                """,
                user_id, source
            )
        finally:
            await conn.close()
        return

    async with _batch_lock:
        _source_batch_data[(user_id, source)] += 1
        if len(_source_batch_data) >= _batch_size:
            await _process_source_batch()

