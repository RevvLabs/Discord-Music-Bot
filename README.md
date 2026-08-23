<div align="center">

# 🎵 Mewzik Bot

**A multi-bot Discord music system built on discord.py + Lavalink.**
One codebase runs any number of bots — each with its own token, config, database, and emoji set — with automatic sharding and clustering.

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-latest-5865F2?logo=discord&logoColor=white)
![Lavalink](https://img.shields.io/badge/Lavalink-v4-FB7299)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-per--bot-4169E1?logo=postgresql&logoColor=white)

</div>

---

## 📑 Contents

- [✨ Features](#-features)
- [🎮 Commands](#-commands)
- [📦 Requirements](#-requirements)
- [🚀 Quick Start](#-quick-start)
- [🤖 Running Multiple Bots](#-running-multiple-bots)
- [🗂️ Project Layout](#️-project-layout)
- [🔐 Security Notes](#-security-notes)

---

## ✨ Features

| | |
|---|---|
| 🎧 **Wide source support** | YouTube, YouTube Music, Spotify, Deezer, Apple Music, JioSaavn, SoundCloud & more (via Lavalink + LavaSrc) |
| 📝 **Lyrics** | lrclib + Lavalyrics fallback, romanization for non-Latin scripts |
| 🔁 **Autoplay** | Admin-curated playlists shared across all bots |
| ⚙️ **Per-server setup** | Exact channel binding (`/setup`) or category binding (`/temp-setup`) |
| 🎚️ **DJ controls** | DJ roles, per-command DJ locks, session locking |
| ⭐ **Personal** | Favorites, playlists, profiles with image cards, listening leaderboards |
| 🛡️ **Anti-spam** | Auto-blacklist for command spammers + manual owner controls |
| 📈 **Scales itself** | Automatic shard/cluster topology (1 shard / 1200 guilds, 3 shards / cluster — tunable) |

---

## 🎮 Commands

<table>
<tr><th>Playback</th><th>Queue</th><th>Personal & Setup</th></tr>
<tr valign="top"><td>

`play` · `search` · `pause`
`resume` · `skip` · `previous`
`seek` · `replay` · `loop`
`volume` · `filters` · `stop`
`disconnect` · `now_playing`
`lyrics`

</td><td>

`queue` · `shuffle` · `move`
`remove` · `clear` · `history`
`autoplay`

</td><td>

`favorites` · `save_favorite`
`playlist` · `profile`
`leaderboard` · `setup`
`temp-setup` · `dj` · `dedicate`
`session` · `ping` · `stats`

</td></tr>
</table>

---

## 📦 Requirements

| Requirement | Version / Notes |
|---|---|
| 🐍 **Python** | **3.10+** (3.12 recommended) |
| 🐘 **PostgreSQL** | Any recent version — **one database per bot** |
| ☕ **Java** | 17+ (to run the Lavalink server) |
| 🎶 **Lavalink** | v4 — config template in `application.yml.example` |

---

## 🚀 Quick Start

### 1️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Set up PostgreSQL

```sql
CREATE DATABASE mybot;
```

> Tables are created automatically on first run — no migrations needed.

### 3️⃣ Set up Lavalink

1. Download **Lavalink v4** from [lavalink-devs/Lavalink releases](https://github.com/lavalink-devs/Lavalink/releases).
2. Copy `application.yml.example` → `application.yml` next to the Lavalink jar and fill in the `YOUR_*` placeholders (Spotify keys, Deezer ARL, etc. — each has a comment explaining where to get it).
3. Run it:
   ```bash
   java -jar Lavalink.jar
   ```

> The bot connects using `NODE_1_URI` / `NODE_1_PASSWORD` from its `.env` — these must match `server.port` and `lavalink.server.password` in `application.yml`.

### 4️⃣ Configure your bot

```bash
cp bots/bot1/.env.example bots/bot1/.env
```

Every variable is documented with comments in the template. The essentials:
`TOKEN` · `DATABASE_URL` · `NODE_1_URI` · `NODE_1_PASSWORD` · `BOT_OWNER_IDS`

> Also set your emoji IDs in `bots/bot1/emojis.py` — see [bots/README.md](bots/README.md) for the full walkthrough (Developer Portal intents, invite link, obtaining emoji codes).

### 5️⃣ Run

```bash
python launcher.py              # start every bot in bots/
python launcher.py --bot=bot1   # start one bot
```

> Sharding and clustering are automatic. Tune with `GUILDS_PER_SHARD` / `SHARDS_PER_CLUSTER` in the bot's `.env` (defaults: 1200 / 3).

---

## 🤖 Running Multiple Bots

Each subfolder of `bots/` containing a `.env` becomes its own bot — separate token, config, database, and emojis.

📖 **Full guide:** [bots/README.md](bots/README.md)

---

## 🗂️ Project Layout

```
launcher.py              entry point — multi-bot spawner → cluster launcher → shard workers
bots/<name>/             per-bot config: .env + emojis.py
cogs/commands/           user commands (auto-discovered)
cogs/owner_commands/     owner-only commands
cogs/events/             event handlers (player events, auto-join, auto-stop, errors)
database/                table schemas (created automatically at startup)
utils/                   cache manager, player class, embed designs, helpers
json_Data/               runtime data shared across bots (autoplay playlists, maintenance state)
application.yml.example  Lavalink server config template
```

---

## 🔐 Security Notes

- ❌ **Never commit** `.env` or `application.yml` — both are gitignored; ship the `.example` templates instead.
- 🔑 `BOT_OWNER_IDS` grants access to owner commands **and jishaku** (code execution on the host) — keep it to yourself.
