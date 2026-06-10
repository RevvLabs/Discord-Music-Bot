"""
Spotify playlist / album scraper.

Fetches track names from Spotify's embed page __NEXT_DATA__ JSON — no API key
required, no OAuth, no rate-limit headaches.

Returns a SpotifyPlaylistResult dataclass with:
  sp_type    – "playlist" or "album"
  pl_name    – human-readable title (falls back to sp_type.title())
  tracks     – list of "Track Name Artist Name" strings ready for search
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List
from urllib.parse import urlparse

import ssl
import aiohttp

# Windows doesn't ship root CA certificates that Python's ssl module can use,
# so we create a permissive SSL context that skips certificate chain verification.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

_EMBED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
    re.DOTALL,
)


@dataclass
class SpotifyPlaylistResult:
    sp_type: str
    pl_name: str
    tracks: List[str] = field(default_factory=list)              # "Title Artist" search strings
    track_pairs: List[tuple] = field(default_factory=list)        # (title, artist) tuples


def _find_track_list(obj, depth: int = 0):
    """Recursively search for the first 'trackList' list in a JSON object."""
    if depth > 12:
        return []
    if isinstance(obj, dict):
        if "trackList" in obj and isinstance(obj["trackList"], list):
            return obj["trackList"]
        for v in obj.values():
            result = _find_track_list(v, depth + 1)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _find_track_list(item, depth + 1)
            if result:
                return result
    return []


async def scrape_spotify_playlist(url: str) -> SpotifyPlaylistResult | None:
    """
    Scrape track names for a Spotify playlist or album URL.

    Args:
        url: Full Spotify playlist/album URL (tracking params already stripped).

    Returns:
        SpotifyPlaylistResult on success, None if scraping failed or no tracks found.
    """
    path = urlparse(url).path
    sp_type = "playlist" if "/playlist/" in url else "album"
    sp_id = path.split("/")[-1]
    embed_url = f"https://open.spotify.com/embed/{sp_type}/{sp_id}"

    connector = aiohttp.TCPConnector(ssl=_SSL_CTX)
    async with aiohttp.ClientSession(headers=_EMBED_HEADERS, connector=connector) as session:
        async with session.get(embed_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            html = await resp.text()

        match = _NEXT_DATA_RE.search(html)
        if not match:
            return None

        next_data = json.loads(match.group(1))

        # Attempt to extract the playlist / album name from the data tree
        pl_name = sp_type.title()
        try:
            entity = (
                next_data["props"]["pageProps"]
                .get("state", {})
                .get("data", {})
                .get(sp_type, {})
            )
            pl_name = entity.get("name", pl_name) or pl_name
        except Exception:
            pass

        # Try oEmbed as a name fallback while we still have the session
        if pl_name == sp_type.title():
            try:
                oembed_url = f"https://open.spotify.com/oembed?url={url}"
                async with session.get(oembed_url, timeout=aiohttp.ClientTimeout(total=5)) as oe_resp:
                    if oe_resp.status == 200:
                        oe_data = await oe_resp.json()
                        pl_name = oe_data.get("title", pl_name)
            except Exception:
                pass

        track_list = _find_track_list(next_data)
        if not track_list:
            return None

        tracks = []
        track_pairs = []
        for item in track_list:
            title = item.get("title", "").strip()
            subtitle = item.get("subtitle", "").strip()
            if title:
                entry = f"{title} {subtitle}".strip() if subtitle else title
                tracks.append(entry)
                track_pairs.append((title, subtitle))

        if not tracks:
            return None

        return SpotifyPlaylistResult(
            sp_type=sp_type, pl_name=pl_name, tracks=tracks, track_pairs=track_pairs
        )
