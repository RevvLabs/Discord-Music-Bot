# Mewzik Bot

A multi-bot Discord music system built on discord.py and Lavalink. One codebase runs any number of bots, each with its own token, config, database, and emoji set — with automatic sharding and clustering as the bots grow.

## Features

- Music playback from YouTube, YouTube Music, Spotify, Deezer, Apple Music, JioSaavn, SoundCloud and more (via Lavalink + LavaSrc)
- Lyrics (lrclib + Lavalyrics fallback, romanization for non-Latin scripts)
- Autoplay system with admin-curated playlists shared across all bots
- Per-server setup modes: exact channel binding (`/setup`) or category binding (`/temp-setup`)
- DJ roles, per-command DJ locks, session locking
- Favorites, playlists, profiles with image cards, listening leaderboards
- Auto-blacklist for command spammers + manual owner controls
- Automatic shard/cluster topology (1 shard per 1200 guilds, 3 shards per cluster — tunable via env)

## Requirements

| Requirement | Version / Notes |
|---|---|
| Python | **3.10 or newer** (3.12 recommended) |
| PostgreSQL | any recent version; one database **per bot** |
| Java | 17+ (to run the Lavalink server) |
| Lavalink | v4 — config template in `application.yml.example` |

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up PostgreSQL

Create a database for your bot:

```sql
CREATE DATABASE mybot;
```

Tables are created automatically on first run — no migrations needed.

### 3. Set up Lavalink

1. Download Lavalink v4 from [lavalink-devs/Lavalink releases](https://github.com/lavalink-devs/Lavalink/releases)
2. Copy `application.yml.example` to `application.yml` next to the Lavalink jar and fill in the `YOUR_*` placeholders (Spotify API keys, Deezer ARL, etc. — each has a comment explaining where to get it)
3. Run it: `java -jar Lavalink.jar`

The bot connects to it using `NODE_1_URI` / `NODE_1_PASSWORD` from the bot's `.env` — these must match `server.port` and `lavalink.server.password` in `application.yml`.

### 4. Configure your bot

```bash
# copy the documented template and fill it in
cp bots/bot1/.env.example bots/bot1/.env
```

Every variable is explained with comments in the template. The essentials: `TOKEN`, `DATABASE_URL`, `NODE_1_URI`, `NODE_1_PASSWORD`, `BOT_OWNER_IDS`.

Also set up `bots/bot1/emojis.py` with your own emoji IDs — see [bots/README.md](bots/README.md) for the full walkthrough, including Discord Developer Portal steps (intents, invite link) and how to obtain emoji codes.

### 5. Run

```bash
python launcher.py              # start every bot in bots/
python launcher.py --bot=bot1   # start one bot
```

Sharding and clustering are automatic. To tune them, set `GUILDS_PER_SHARD` / `SHARDS_PER_CLUSTER` in the bot's `.env` (defaults: 1200 / 3).

## Running multiple bots

Each subfolder of `bots/` containing a `.env` becomes a bot. Full guide: [bots/README.md](bots/README.md).

## Project layout

```
launcher.py            entry point — multi-bot spawner → cluster launcher → shard workers
bots/<name>/           per-bot config: .env + emojis.py
cogs/commands/         user commands (auto-discovered)
cogs/owner_commands/   owner-only commands
cogs/events/           event handlers (player events, auto-join, auto-stop, errors)
database/              table schemas (created automatically at startup)
utils/                 cache manager, player class, embed designs, helpers
json_Data/             runtime data shared across bots (autoplay playlists, maintenance state)
application.yml.example  Lavalink server config template
```

## Security notes

- Never commit `.env` or `application.yml` — both are gitignored; ship the `.example` templates instead
- `BOT_OWNER_IDS` grants access to owner commands **and jishaku** (code execution on the host) — keep it to yourself
