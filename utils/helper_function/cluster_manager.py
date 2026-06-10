import json
import math
import os
from pathlib import Path

import aiohttp

def _env_int(name: str, default: int) -> int:
    """Read a positive int from env; fall back to default on missing/invalid."""
    try:
        value = int(os.getenv(name, ""))
        return value if value > 0 else default
    except ValueError:
        return default


GUILDS_PER_SHARD = _env_int("GUILDS_PER_SHARD", 1200)
SHARDS_PER_CLUSTER = _env_int("SHARDS_PER_CLUSTER", 3)
_DISCORD_API = "https://discord.com/api/v10"


async def get_recommended_shards(token: str) -> int:
    """Ask Discord how many shards this bot needs based on its guild count."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_DISCORD_API}/gateway/bot",
                headers={"Authorization": f"Bot {token}"},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return max(1, data.get("shards", 1))
                print(f"[CLUSTER] Gateway/bot returned HTTP {resp.status}")
    except Exception as e:
        print(f"[CLUSTER] Failed to fetch recommended shards: {e}")
    return 1


def calculate_clusters(shard_count: int) -> int:
    return max(1, math.ceil(shard_count / SHARDS_PER_CLUSTER))


def shard_ids_for_cluster(cluster_id: int, total_shards: int, total_clusters: int) -> list:
    per_cluster = math.ceil(total_shards / total_clusters)
    start = cluster_id * per_cluster
    return list(range(total_shards))[start:start + per_cluster]


def cluster_plan(shard_count: int) -> dict:
    """
    Returns topology dict for given shard count.
    Rules: 1 shard per 1200 guilds, 1 cluster per 3 shards.
    """
    cluster_count = calculate_clusters(shard_count)
    return {
        "shard_count": shard_count,
        "cluster_count": cluster_count,
        "assignments": {
            i: shard_ids_for_cluster(i, shard_count, cluster_count)
            for i in range(cluster_count)
        },
    }


# ── Cluster state persistence (per bot, stored in bots/<name>/cluster_state.json) ──

def _state_path(bot_name: str) -> Path:
    return Path("bots") / bot_name / "cluster_state.json"


def load_state(bot_name: str) -> dict:
    p = _state_path(bot_name)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def save_state(bot_name: str, data: dict) -> None:
    p = _state_path(bot_name)
    try:
        existing = load_state(bot_name)
        existing.update(data)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(existing, indent=2))
    except Exception as e:
        print(f"[CLUSTER] Failed to save cluster state: {e}")
