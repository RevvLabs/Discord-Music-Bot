
from utils.helper_function.unified_cache_manager import unified_cache
from utils.logger.mewzik_logger import bot_logger


async def add_favorite(user_id: int, track_url: str, track_title: str):
    """Add a favorite track for user using unified cache."""
    if bot_logger.enabled:
        bot_logger.outgoing(
            "Favorites — add track",
            user_id=user_id,
            track=track_title,
        )
    result = await unified_cache.add_user_favorite(user_id, track_url, track_title)
    if bot_logger.enabled:
        bot_logger.incoming(
            "Favorites — add result",
            user_id=user_id,
            track=track_title,
            success=bool(result),
        )
    return result

async def get_favorites(user_id: int):
    """Get user's favorite tracks using unified cache."""
    result = await unified_cache.get_user_favorites(user_id)
    if bot_logger.enabled:
        bot_logger.debug(
            "Favorites — fetched",
            user_id=user_id,
            count=len(result) if result else 0,
        )
    return result

async def remove_favorite(user_id: int, track_url: str, track_title: str = None):
    """Remove a favorite track for user using unified cache."""
    # If track_title is not provided, we need to find it from the user's favorites
    if track_title is None:
        favorites = await unified_cache.get_user_favorites(user_id)
        for fav_url, fav_title in favorites:
            if fav_url == track_url:
                if bot_logger.enabled:
                    bot_logger.outgoing(
                        "Favorites — remove track",
                        user_id=user_id,
                        track=fav_title,
                    )
                return await unified_cache.remove_user_favorite(user_id, track_url, fav_title)
        if bot_logger.enabled:
            bot_logger.debug(
                "Favorites — track not found for removal",
                user_id=user_id,
            )
        return False

    if bot_logger.enabled:
        bot_logger.outgoing(
            "Favorites — remove track",
            user_id=user_id,
            track=track_title,
        )
    return await unified_cache.remove_user_favorite(user_id, track_url, track_title)
