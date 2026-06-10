import sys
import os

# ========================================================================================
# EARLY ARG PARSING — must run before any other imports so env vars are set first
# ========================================================================================
def _parse_args():
    argv = sys.argv[1:]
    bot_name = cluster_id = shard_ids = shard_count = None
    for i, arg in enumerate(argv):
        if arg.startswith('--bot='):
            bot_name = arg.split('=', 1)[1]
        elif arg == '--bot' and i + 1 < len(argv):
            bot_name = argv[i + 1]
        elif arg.startswith('--cluster='):
            cluster_id = int(arg.split('=', 1)[1])
        elif arg.startswith('--shard-ids='):
            shard_ids = [int(x) for x in arg.split('=', 1)[1].split(',') if x]
        elif arg.startswith('--shard-count='):
            shard_count = int(arg.split('=', 1)[1])
    return bot_name, cluster_id, shard_ids, shard_count


_BOT_NAME, _CLUSTER_ID, _SHARD_IDS, _SHARD_COUNT = _parse_args()

if _BOT_NAME:
    os.environ["BOT_NAME"] = _BOT_NAME
    if _CLUSTER_ID is not None:
        os.environ["CLUSTER_ID"] = str(_CLUSTER_ID)
    _BOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bots', _BOT_NAME)
    if os.path.isdir(_BOT_DIR):
        sys.path.insert(0, _BOT_DIR)
        _env_file = os.path.join(_BOT_DIR, '.env')
        if os.path.isfile(_env_file):
            from dotenv import load_dotenv as _load_env
            _load_env(dotenv_path=_env_file, override=True)

# ========================================================================================
# STANDARD IMPORTS (after env is loaded)
# ========================================================================================
import asyncio
import subprocess
from datetime import datetime, timezone
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.bot_starter.change_presence import change_presence
from utils.bot_starter.initialize_db import initialize_databases
from utils.bot_starter.load_cogs import load_cogs
from utils.bot_starter.sync_commands import sync_commands
from utils.connection.lava_link_connection import connect_to_lavalink
from utils.helper_function.get_prefix import get_prefix
from utils.colours.colours import *
from utils.logger.mewzik_logger import bot_logger
from utils.helper_function.cluster_manager import (
    get_recommended_shards, cluster_plan, save_state,
    GUILDS_PER_SHARD, SHARDS_PER_CLUSTER,
)

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.guild_messages = True
intents.message_content = True

def _parse_owner_ids() -> set:
    raw = os.getenv("BOT_OWNER_IDS", "")
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids

_OWNER_IDS = _parse_owner_ids()


# ========================================================================================
# BOT FACTORY
# ========================================================================================

def _make_bot(shard_ids=None, shard_count=None):
    """
    shard_ids + shard_count → multi-cluster worker (commands.Bot with explicit shards).
    shard_count only         → single-cluster AutoShardedBot with fixed shard count.
    neither                  → AutoShardedBot, Discord decides shard count.
    """
    kwargs = dict(
        command_prefix=get_prefix,
        intents=intents,
        help_command=None,
        chunk_guilds_at_startup=False,
        owner_ids=_OWNER_IDS,
        case_insensitive=True,
    )
    if shard_ids is not None and shard_count is not None:
        return commands.Bot(shard_ids=shard_ids, shard_count=shard_count, **kwargs)
    if shard_count and shard_count > 1:
        return commands.AutoShardedBot(shard_count=shard_count, **kwargs)
    return commands.AutoShardedBot(**kwargs)


# ========================================================================================
# EVENT REGISTRATION
# ========================================================================================

def _register_events(bot):
    @bot.check
    async def _guild_only(ctx):
        # Music bot — every command needs a guild. DM invocations raise
        # CheckFailure, which the error handler silently ignores.
        return ctx.guild is not None

    async def setup_hook():
        try:
            if bot_logger.enabled:
                bot_logger.info("Loading cogs")
            await load_cogs(bot)
            if bot_logger.enabled:
                bot_logger.info("All cogs loaded successfully")
        except Exception as e:
            print(f"\033[91m[ERROR] Cogs Load Error\033[0m: {e}")

        # Only cluster 0 (or single-cluster) syncs slash commands to avoid rate-limit spam
        if _CLUSTER_ID is None or _CLUSTER_ID == 0:
            try:
                if bot_logger.enabled:
                    bot_logger.outgoing("Syncing slash commands")
                await sync_commands(bot)
            except Exception as e:
                print(f"\033[91m[ERROR] Commands Sync Error\033[0m: {e}")

    bot.setup_hook = setup_hook

    @bot.event
    async def on_ready():
        if getattr(bot, "_ready_fired", False):
            return
        bot._ready_fired = True

        try:
            bot.start_time = datetime.now(timezone.utc)
        except Exception:
            pass

        guild_count = len(bot.guilds)
        cluster_label = f"Cluster {_CLUSTER_ID}" if _CLUSTER_ID is not None else "Single"
        shard_label = (
            f"shards {_SHARD_IDS}"
            if _SHARD_IDS
            else f"shard_count={getattr(bot, 'shard_count', 1)}"
        )

        if bot_logger.enabled:
            bot_logger.info(
                "Bot on_ready fired",
                bot=str(bot.user),
                bot_id=bot.user.id,
                guild_count=guild_count,
                cluster=cluster_label,
                shards=shard_label,
            )

        print(f"[{cluster_label}] {bot.user} ready | guilds={guild_count} | {shard_label}")

        # Persist live guild count per cluster for topology recalculation on restart
        if _BOT_NAME:
            key = f"guild_count_cluster_{_CLUSTER_ID}" if _CLUSTER_ID is not None else "guild_count"
            save_state(_BOT_NAME, {key: guild_count})
            asyncio.create_task(_guild_count_tracker(bot))

        try:
            await bot.load_extension("jishaku")
            if bot_logger.enabled:
                bot_logger.info("Jishaku extension loaded")
        except Exception as e:
            print(f"\033[91m[ERROR] Jishaku Load Error\033[0m: {e}")

        try:
            if bot_logger.enabled:
                bot_logger.outgoing("Connecting to Lavalink nodes")
            await connect_to_lavalink(bot)
        except Exception as e:
            print(f"\033[91m[ERROR] Lavalink Connection Error\033[0m: {e}")

        try:
            await change_presence(bot)
            if bot_logger.enabled:
                bot_logger.info("Bot presence updated")
        except Exception as e:
            print(f"\033[91m[ERROR] Presence Update Error\033[0m: {e}")

    @bot.event
    async def on_connect():
        if getattr(bot, "_connect_logged", False):
            return
        bot._connect_logged = True
        if bot_logger.enabled:
            bot_logger.info("Bot connected to Discord gateway")

    return bot


async def _guild_count_tracker(bot):
    """Background task: save live guild count every 5 minutes for topology decisions."""
    while not bot.is_closed():
        await asyncio.sleep(300)
        if _BOT_NAME:
            key = f"guild_count_cluster_{_CLUSTER_ID}" if _CLUSTER_ID is not None else "guild_count"
            save_state(_BOT_NAME, {key: len(bot.guilds)})


# ========================================================================================
# CLUSTER LAUNCHER — runs once per bot name; decides shard/cluster topology
# ========================================================================================

async def run_cluster_launcher(bot_name: str):
    print(f"\n[CLUSTER] Fetching recommended shard count for {bot_name}...")
    shard_count = await get_recommended_shards(TOKEN)
    plan = cluster_plan(shard_count)
    cluster_count = plan["cluster_count"]

    print(
        f"[CLUSTER] Topology → shards={shard_count} clusters={cluster_count} "
        f"(1 shard/{GUILDS_PER_SHARD} guilds · {SHARDS_PER_CLUSTER} shards/cluster)"
    )
    save_state(bot_name, {
        "shard_count": shard_count,
        "cluster_count": cluster_count,
        "guilds_per_shard": GUILDS_PER_SHARD,
        "shards_per_cluster": SHARDS_PER_CLUSTER,
    })

    if cluster_count == 1:
        # Single cluster: run in-process — no subprocess overhead
        print(f"[CLUSTER] Single cluster — running in-process")
        await initialize_databases()
        bot = _make_bot(shard_count=shard_count if shard_count > 1 else None)
        _register_events(bot)
        await bot.start(TOKEN)
    else:
        # Multi-cluster: spawn one worker subprocess per cluster
        print(f"[CLUSTER] Spawning {cluster_count} cluster workers...")
        script = os.path.abspath(sys.argv[0])
        procs = []
        for cid, sids in plan["assignments"].items():
            shard_ids_str = ",".join(str(s) for s in sids)
            cmd = [
                sys.executable, script,
                f"--bot={bot_name}",
                f"--cluster={cid}",
                f"--shard-ids={shard_ids_str}",
                f"--shard-count={shard_count}",
            ]
            p = subprocess.Popen(cmd)
            procs.append((cid, p))
            print(f"[CLUSTER] Spawned cluster {cid} shards={sids} (PID {p.pid})")

        try:
            for _, p in procs:
                p.wait()
        except KeyboardInterrupt:
            print("\n[CLUSTER] Shutting down all clusters...")
            for _, p in procs:
                p.terminate()
            for _, p in procs:
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
            print("[CLUSTER] All clusters stopped.")


# ========================================================================================
# WORKER ENTRY — runs in each cluster subprocess (--cluster=N is set)
# ========================================================================================

async def main_worker():
    await initialize_databases()
    bot = _make_bot(shard_ids=_SHARD_IDS, shard_count=_SHARD_COUNT)
    _register_events(bot)
    await bot.start(TOKEN)


# ========================================================================================
# MULTI-BOT SPAWNER — spawns one cluster-launcher per bot in bots/
# ========================================================================================

def run_multi_bot_launcher():
    bots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bots')
    if not os.path.isdir(bots_dir):
        print(f"[MULTI-BOT] No 'bots/' directory found.")
        print(f"[MULTI-BOT] Create bots/<name>/.env for each bot.")
        return

    bot_names = sorted([
        d for d in os.listdir(bots_dir)
        if os.path.isdir(os.path.join(bots_dir, d)) and
           os.path.isfile(os.path.join(bots_dir, d, '.env'))
    ])

    if not bot_names:
        print("[MULTI-BOT] No bot directories with .env files found in bots/")
        return

    print(f"\n[MULTI-BOT] Starting {len(bot_names)} bot(s): {', '.join(bot_names)}\n")

    script = os.path.abspath(sys.argv[0])
    procs = []
    for name in bot_names:
        p = subprocess.Popen([sys.executable, script, f'--bot={name}'])
        procs.append((name, p))
        print(f"[MULTI-BOT] Spawned bot '{name}' (PID {p.pid})")

    try:
        for _, p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\n[MULTI-BOT] Shutting down all bots...")
        for _, p in procs:
            p.terminate()
        for _, p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        print("[MULTI-BOT] All bots stopped.")


# ========================================================================================
# ENTRY POINT
# ========================================================================================

if __name__ == "__main__":
    try:
        if _CLUSTER_ID is not None:
            # Worker subprocess with specific shard slice
            asyncio.run(main_worker())
        elif _BOT_NAME:
            # Cluster launcher: fetch topology from Discord, spawn workers or run directly
            asyncio.run(run_cluster_launcher(_BOT_NAME))
        else:
            bots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bots')
            if os.path.isdir(bots_dir):
                run_multi_bot_launcher()
            else:
                # Legacy single-bot mode (no bots/ directory)
                asyncio.run(run_cluster_launcher("default"))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\033[91m[ERROR] Main Entry Point Error\033[0m: {e}")
