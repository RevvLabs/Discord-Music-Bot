"""
Autoplay Playlist Cache Manager
================================
Stores bot-curated playlists (added by admins / AUTOPLAY_CONTROLLERS) with
pre-fetched track data so playback starts instantly without hitting Lavalink
or Spotify search for every track.

Persistence:
  json_Data/autoplay_playlists.json  ← loaded at startup, written on every change

Memory layout:
  _playlists  – list of metadata dicts (id, name, link, platform, track_count, ...)
  _tracks     – dict[playlist_id -> list[track_dict]]
                track_dict keys: uri, title, author, length, artwork, source, query
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from utils.helper_function.spotify_scraper import scrape_spotify_playlist
from utils.logger.mewzik_logger import bot_logger

# Shared across ALL bots — a playlist added/fetched by one bot is instantly
# available to every other bot reading the same file.
_CACHE_FILE = "json_Data/autoplay_playlists_shared.json"

_SPOTIFY_DOMAINS = ("open.spotify.com", "spotify.com")
_YOUTUBE_DOMAINS = ("youtube.com", "youtu.be", "music.youtube.com")

# Delay between spsearch calls during Spotify prefetch.
# 100 tracks × 0.35 s ≈ 35 s total — prevents Lavalink / YouTube rate-limits.
_SPSEARCH_DELAY = 0.35

# Batch size: log progress every N tracks so admins can see it working.
_LOG_EVERY = 10


class AutoplayCacheManager:
    def __init__(self):
        self._playlists: List[dict] = []
        self._tracks: Dict[str, List[dict]] = {}
        self._sessions: Dict[int, dict] = {}   # guild_id -> session state
        self._lock = asyncio.Lock()
        self._file_mtime: float = 0.0   # last-seen mtime of the shared cache file
        self._load_from_disk()

    # ── Disk I/O ──────────────────────────────────────────────────────────────

    def _load_from_disk(self):
        """Load playlist metadata and cached tracks from JSON. Called at startup (sync)."""
        if not os.path.exists(_CACHE_FILE):
            self._playlists = []
            self._tracks = {}
            self._file_mtime = 0.0
            return
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._playlists = data.get("playlists", [])
            raw_tracks = data.get("tracks", {})
            self._tracks = {}
            for pl in self._playlists:
                pid = pl["id"]
                self._tracks[pid] = raw_tracks.get(pid, [])
            try:
                self._file_mtime = os.path.getmtime(_CACHE_FILE)
            except OSError:
                self._file_mtime = 0.0
            if bot_logger.enabled:
                bot_logger.debug(
                    "Autoplay cache loaded from disk",
                    playlist_count=len(self._playlists),
                )
        except Exception as e:
            print(f"[AutoplayCache] Failed to load from disk: {e}")
            self._playlists = []
            self._tracks = {}
            self._file_mtime = 0.0

    def _reload_if_changed(self):
        """Reload from disk if another bot has written a newer version of the file."""
        try:
            current = os.path.getmtime(_CACHE_FILE)
        except OSError:
            return  # file doesn't exist yet — nothing to reload
        if current > self._file_mtime:
            self._load_from_disk()

    def _save_to_disk(self):
        """Persist current state to JSON (synchronous write — called under lock)."""
        try:
            os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
            data = {
                "playlists": self._playlists,
                "tracks": self._tracks,
            }
            with open(_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            try:
                self._file_mtime = os.path.getmtime(_CACHE_FILE)
            except OSError:
                pass
        except Exception as e:
            print(f"[AutoplayCache] Failed to save to disk: {e}")

    # ── Platform helpers ──────────────────────────────────────────────────────

    def _platform(self, link: str) -> str:
        ll = link.lower()
        if any(d in ll for d in _SPOTIFY_DOMAINS):
            return "Spotify"
        if any(d in ll for d in _YOUTUBE_DOMAINS):
            return "YouTube"
        return "Unknown"

    def _is_spotify_playlist(self, link: str) -> bool:
        ll = link.lower()
        return any(d in ll for d in _SPOTIFY_DOMAINS) and any(
            seg in ll for seg in ("/playlist/", "/album/")
        )

    def _is_youtube_playlist(self, link: str) -> bool:
        ll = link.lower()
        return any(d in ll for d in _YOUTUBE_DOMAINS) and (
            "list=" in ll or "/playlist" in ll
        )

    # ── Public read API ───────────────────────────────────────────────────────

    def get_playlists(self) -> List[dict]:
        """Return list of all playlist metadata dicts."""
        self._reload_if_changed()
        return list(self._playlists)

    def get_playlist_by_id(self, playlist_id: str) -> Optional[dict]:
        self._reload_if_changed()
        return next((p for p in self._playlists if p["id"] == playlist_id), None)

    def get_tracks(self, playlist_id: str) -> List[dict]:
        """Return a copy of the cached track list for a playlist."""
        self._reload_if_changed()
        return list(self._tracks.get(playlist_id, []))

    def get_all_tracks(self) -> List[dict]:
        """Return all tracks from all playlists (for Play All)."""
        self._reload_if_changed()
        result = []
        for pl in self._playlists:
            result.extend(self._tracks.get(pl["id"], []))
        return result

    # ── Prefetch helpers ──────────────────────────────────────────────────────

    async def _prefetch_spotify(self, link: str) -> Tuple[List[dict], str]:
        """Scrape Spotify and resolve each track via spsearch. Returns (tracks, error_msg)."""
        import voltricx

        clean_link = link.split("?")[0]
        sp_result = await scrape_spotify_playlist(clean_link)
        if not sp_result or not sp_result.tracks:
            return [], "Could not scrape this Spotify playlist. It may be private or invalid."

        total = len(sp_result.tracks)
        tracks: List[dict] = []

        for idx, query in enumerate(sp_result.tracks, start=1):
            # Throttle: pause between each spsearch to avoid hammering Lavalink / YouTube
            if idx > 1:
                await asyncio.sleep(_SPSEARCH_DELAY)

            if idx % _LOG_EVERY == 0 or idx == total:
                print(f"[AutoplayCache] Prefetching Spotify tracks: {idx}/{total}")

            try:
                results = await voltricx.Playable.search(query, source="spsearch")
                t = None
                if results:
                    if isinstance(results, voltricx.Playlist):
                        t = results.tracks[0] if results.tracks else None
                    else:
                        t = results[0]
                if t:
                    tracks.append({
                        "encoded": getattr(t, "encoded", None),
                        "uri": t.uri,
                        "title": t.title,
                        "author": getattr(t, "author", ""),
                        "length": getattr(t, "length", 0),
                        "artwork": getattr(t, "artwork", None),
                        "source": getattr(t, "source", "spsearch"),
                        "query": query,
                    })
                else:
                    tracks.append({
                        "encoded": None, "uri": None, "title": query, "author": "", "length": 0,
                        "artwork": None, "source": "spsearch", "query": query,
                    })
            except Exception:
                tracks.append({
                    "encoded": None, "uri": None, "title": query, "author": "", "length": 0,
                    "artwork": None, "source": "spsearch", "query": query,
                })

        return tracks, ""

    async def _prefetch_youtube(self, link: str) -> Tuple[List[dict], str]:
        """Resolve a YouTube playlist via Lavalink. Returns (tracks, error_msg)."""
        import voltricx

        try:
            results = await voltricx.Playable.search(link)
        except Exception as e:
            return [], f"Lavalink error: {e}"

        if not results:
            return [], "Could not load this YouTube playlist. It may be private or invalid."

        if isinstance(results, voltricx.Playlist):
            raw = getattr(results, "tracks", [])[:200]
        else:
            raw = results[:200]

        tracks: List[dict] = []
        for t in raw:
            tracks.append({
                "encoded": getattr(t, "encoded", None),
                "uri": t.uri,
                "title": t.title,
                "author": getattr(t, "author", ""),
                "length": getattr(t, "length", 0),
                "artwork": getattr(t, "artwork", None),
                "source": getattr(t, "source", "youtube"),
                "query": None,
            })
        return tracks, ""

    # ── Mutating API ──────────────────────────────────────────────────────────

    async def add_playlist(
        self, name: str, link: str, added_by: int
    ) -> Tuple[bool, int, str]:
        """
        Add and pre-fetch a playlist.
        Returns (success, track_count, error_message).
        Must be called from an async context with Lavalink connected.
        """
        platform = self._platform(link)
        if platform == "Unknown":
            return False, 0, "Only Spotify and YouTube playlists are supported."

        async with self._lock:
            if any(p["name"].lower() == name.lower() for p in self._playlists):
                return False, 0, f"A playlist named **{name}** already exists."

            playlist_id = str(uuid.uuid4())[:8]

            if self._is_spotify_playlist(link):
                tracks, err = await self._prefetch_spotify(link)
            elif self._is_youtube_playlist(link):
                tracks, err = await self._prefetch_youtube(link)
            else:
                return False, 0, "Unsupported link. Provide a Spotify or YouTube playlist URL."

            if err:
                return False, 0, err
            if not tracks:
                return False, 0, "No tracks could be fetched from this playlist."

            pl_meta = {
                "id": playlist_id,
                "name": name,
                "link": link,
                "platform": platform,
                "track_count": len(tracks),
                "added_by": added_by,
                "added_at": datetime.now(timezone.utc).isoformat(),
            }
            self._playlists.append(pl_meta)
            self._tracks[playlist_id] = tracks
            self._save_to_disk()

            if bot_logger.enabled:
                bot_logger.debug(
                    "Autoplay playlist added",
                    name=name,
                    platform=platform,
                    tracks=len(tracks),
                )
            return True, len(tracks), ""

    def remove_playlist(self, playlist_id: str) -> bool:
        """Remove a playlist and its cached tracks from memory and disk."""
        pl = self.get_playlist_by_id(playlist_id)
        if not pl:
            return False
        self._playlists = [p for p in self._playlists if p["id"] != playlist_id]
        self._tracks.pop(playlist_id, None)
        self._save_to_disk()
        if bot_logger.enabled:
            bot_logger.debug("Autoplay playlist removed", playlist_id=playlist_id)
        return True

    # ── Per-guild session API ─────────────────────────────────────────────────

    def start_session(self, guild_id: int, tracks: List[dict], position: int, requestor) -> None:
        """Register a smart-queue autoplay session for a guild."""
        self._sessions[guild_id] = {
            "tracks": tracks,
            "position": position,
            "requestor": requestor,
        }

    def stop_session(self, guild_id: int) -> None:
        """Remove the autoplay session for a guild."""
        self._sessions.pop(guild_id, None)

    def has_session(self, guild_id: int) -> bool:
        return guild_id in self._sessions

    def get_session(self, guild_id: int) -> Optional[dict]:
        return self._sessions.get(guild_id)

    def advance_session(self, guild_id: int, count: int) -> List[dict]:
        """
        Pull the next `count` tracks from the session and advance the position.
        Wraps around to the beginning when exhausted so the playlist loops
        indefinitely until stop_session() is called explicitly.
        """
        session = self._sessions.get(guild_id)
        if not session:
            return []
        tracks = session["tracks"]
        if not tracks:
            return []
        pos = session["position"] % len(tracks)
        batch = tracks[pos: pos + count]
        if not batch:
            pos = 0
            batch = tracks[0:count]
        session["position"] = (pos + len(batch)) % len(tracks)
        return batch


# ── Singleton ─────────────────────────────────────────────────────────────────
autoplay_cache = AutoplayCacheManager()
