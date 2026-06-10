import asyncio

# Global semaphore: limits concurrent Lavalink track searches across ALL guilds.
# Keeps the node from being hammered when multiple users load playlists at once.
LAVALINK_SEARCH_SEM = asyncio.Semaphore(5)
