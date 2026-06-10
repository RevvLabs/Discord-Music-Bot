# Running Multiple Bots from One Codebase

This codebase supports running any number of Discord bots at the same time, all sharing the same code. Each bot lives in its own folder inside `bots/` and only needs two files: a `.env` (its config) and an `emojis.py` (its emoji IDs).

## How it works

When you run the launcher with no arguments:

```
python launcher.py
```

it scans the `bots/` directory, finds every subfolder that contains a `.env` file, and spawns one process per bot:

```
bots/
├── bot1/
│   ├── .env          ← bot1's token, database, lavalink, etc.
│   └── emojis.py     ← bot1's custom emoji IDs
├── bot2/
│   ├── .env          ← bot2's config
│   └── emojis.py     ← bot2's emoji IDs
└── README.md         ← this file
```

Each bot process loads **its own** `.env` and `emojis.py` — the folder is put first on the Python path, so `from emojis import ...` anywhere in the code resolves to that bot's file. Sharding/clustering is handled automatically per bot based on its guild count.

You can also run a single bot directly:

```
python launcher.py --bot=bot1
```

## Adding a new bot (step by step)

### 1. Create the bot on Discord

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. Under **Bot**: click **Reset Token** and copy the token (you'll need it for `.env`).
3. Under **Bot → Privileged Gateway Intents**: enable **Server Members Intent** and **Message Content Intent**.
4. Under **OAuth2 → URL Generator**: select `bot` + `applications.commands` scopes, pick permissions (at minimum: Send Messages, Embed Links, Connect, Speak), and use the generated URL to invite the bot to your server.

### 2. Create the bot folder

Copy an existing bot folder as a starting point:

```
# Windows (PowerShell)
Copy-Item -Recurse bots/bot1 bots/mynewbot

# Linux / macOS
cp -r bots/bot1 bots/mynewbot
```

The folder name (`mynewbot`) is the bot's internal name — lowercase, no spaces.

> Starting from scratch instead? Copy `bots/bot1/.env.example` to `bots/mynewbot/.env` and copy `bots/bot1/emojis.py` too. **Both files are required** — the bot won't start without `emojis.py`.

### 3. Fill in the `.env`

Open `bots/mynewbot/.env` and change at least these values:

| Variable | What to put |
|---|---|
| `TOKEN` | The new bot's token from step 1 |
| `BOT_NAME` | Display name for this bot |
| `PREFIX` | Command prefix (e.g. `!` or `.`) |
| `DATABASE_URL` / `PG_*` | **A separate database for this bot** (see below) |
| `LOG_FILE_PATH` | A unique log file, e.g. `logs/mynewbot.log` |
| `BOT_OWNER_IDS` | Your Discord user ID(s) |
| `MAIN_SERVER`, `BACKUP_CHANNEL_ID`, `BLACKLIST_WEBHOOK_URL` | Your support-server IDs/webhook |
| `NODE_1_URI` / `NODE_1_PASSWORD` | Your Lavalink node (bots **can** share the same node) |

Every variable is documented with comments in `bots/bot1/.env.example`.

**Important — separate databases.** Each bot must point at its **own** PostgreSQL database, otherwise bots will overwrite each other's settings, playlists, and favorites. Create one per bot:

```sql
CREATE DATABASE mynewbot;
```

then set `DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/mynewbot` (and the matching `PG_DATABASE=mynewbot`).

### 4. Set up `emojis.py`

The bot uses custom emojis for player buttons, source icons (YouTube, Spotify, …), and pagination arrows. Emoji IDs are tied to the emojis uploaded on a Discord server, and **the bot must be in that server to use them**.

1. Upload your emoji images to a server the new bot is in (Server Settings → Emoji), or add the bot to the server that already hosts them.
2. For each emoji, get its full code: type `\:emojiname:` in Discord chat and send — it prints something like `<:play:1329066423804235788>`.
3. Paste those codes into `bots/mynewbot/emojis.py`, replacing the existing values. Keep the variable names exactly as they are (`PLAY`, `PAUSE`, `PREV_BTN`, `NEXT_BTN`, etc.) — the code imports them by name.

> If the existing emoji IDs come from a server your new bot is also a member of, you can leave `emojis.py` untouched.

### 5. Run

```
python launcher.py
```

The launcher prints one line per bot it found:

```
[MULTI-BOT] Starting 2 bot(s): bot1, mynewbot
[MULTI-BOT] Spawned bot 'bot1' (PID 1234)
[MULTI-BOT] Spawned bot 'mynewbot' (PID 5678)
```

To test only the new bot first:

```
python launcher.py --bot=mynewbot
```

## Removing or disabling a bot

- **Disable temporarily:** rename its `.env` (e.g. to `.env.disabled`) — the launcher only picks up folders that contain a file named exactly `.env`.
- **Remove permanently:** delete the bot's folder.

## Troubleshooting

| Problem | Cause / fix |
|---|---|
| `[MULTI-BOT] No bot directories with .env files found` | Folder is missing a `.env` file, or it's named wrong (must be exactly `.env`) |
| Bot starts but emojis show as blank/broken | Bot is not in the server that hosts those emoji IDs — re-upload emojis to a server the bot is in and update `emojis.py` |
| `ImportError: No module named 'emojis'` | The bot folder is missing `emojis.py` — copy it from `bots/bot1/` |
| Two bots overwrite each other's data | They share a `DATABASE_URL` — give each bot its own database |
| `Improper token has been passed` | Wrong/expired `TOKEN` in that bot's `.env` — reset the token in the Developer Portal |
| Slash commands missing on the new bot | Wait a few minutes after first start (global sync is slow), or restart once |
