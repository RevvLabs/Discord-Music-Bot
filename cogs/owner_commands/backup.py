import discord
from discord.ext import commands, tasks
import shutil
import os
from datetime import datetime
import glob

from utils.embed_designs import owner as owner_design

from dotenv import load_dotenv
load_dotenv()

BOT_OWNER_IDS = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]
BACKUP_CHANNEL_ID = int(os.getenv("BACKUP_CHANNEL_ID", 0)) or None
MAIN_SERVER = int(os.getenv("MAIN_SERVER", 0)) or None

PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE")

class BackupCog(commands.Cog):

    async def backup_tables_to_csv(self, backup_dir, timestamp):
        import asyncpg
        import csv
        table_names = [
            "blacklist",
            "prefixes",
            "player_channels",
            "user_counts",
            "user_engine_selection",
            "user_favorites",
            "user_playlists",
        ]
        csv_folder = os.path.join(backup_dir, f"csv_backup_{timestamp}")
        os.makedirs(csv_folder, exist_ok=True)
        conn = await asyncpg.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASSWORD, database=PG_DATABASE
        )
        try:
            for table in table_names:
                try:
                    rows = await conn.fetch(f'SELECT * FROM "{table}";')
                    if rows:
                        headers = list(rows[0].keys())
                    else:
                        col_query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}';"
                        headers = [r[0] for r in await conn.fetch(col_query)]
                    csv_file = os.path.join(csv_folder, f"{table}.csv")
                    with open(csv_file, "w", newline='', encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(headers)
                        for row in rows:
                            writer.writerow([row[h] for h in headers])
                except Exception as e:
                    print(f"❌ Failed to backup table {table} to CSV: {e}")
        finally:
            await conn.close()
        return csv_folder

    def __init__(self, bot):
        self.bot = bot
        self.backup_to_channel.start()

    def cog_unload(self):
        self.backup_to_channel.cancel()

    def delete_old_backups(self, backup_dir):
        for path in glob.glob(f"{backup_dir}/*"):
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception as e:
                print(f"Failed to delete old backup file or folder {path}: {e}")

    async def perform_backup(self):
        bot_name = os.getenv("BOT_NAME", "default")
        backup_dir = f"backups/{bot_name}"
        os.makedirs(backup_dir, exist_ok=True)
        self.delete_old_backups(backup_dir)

        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        attachments = []

        if PG_HOST and PG_USER and PG_PASSWORD:
            try:
                csv_folder = await self.backup_tables_to_csv(backup_dir, timestamp)
                zip_file = f"{backup_dir}/csv_backup_{timestamp}.zip"
                shutil.make_archive(zip_file.replace('.zip', ''), 'zip', csv_folder)
                attachments.append(discord.File(zip_file))
            except Exception as e:
                print(f"❌ Failed to backup tables to CSV: {e}")
        else:
            print("❌ Missing PostgreSQL credentials in .env")

        bot_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Resolve bot-specific files: check bots/<name>/ first, fall back to root
        def find_bot_file(filename):
            bots_dir = os.path.join(bot_dir, "bots")
            if os.path.isdir(bots_dir):
                for name in os.listdir(bots_dir):
                    candidate = os.path.join(bots_dir, name, filename)
                    if os.path.isfile(candidate):
                        return candidate
            root = os.path.join(bot_dir, filename)
            return root if os.path.isfile(root) else None

        files_to_backup = []
        for fname, suffix in [(".env", ".env"), ("emojis.py", ".py")]:
            src = find_bot_file(fname)
            if src:
                files_to_backup.append((src, f"{backup_dir}/{fname.replace('.', '')}_backup_{timestamp}{suffix}"))
            else:
                print(f"❌ Could not find {fname} to backup")
        for src, dst in files_to_backup:
            try:
                shutil.copy2(src, dst)
                attachments.append(discord.File(dst))
            except Exception as e:
                print(f"❌ Failed to backup `{src}`: {e}")

        return attachments, timestamp

    @tasks.loop(hours=6)
    async def backup_to_channel(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(BACKUP_CHANNEL_ID) if BACKUP_CHANNEL_ID else None
        attachments, timestamp = await self.perform_backup()
        status_msg = None

        if not BACKUP_CHANNEL_ID:
            print("❌ BACKUP_CHANNEL_ID not set in .env.")
            return

        if not channel:
            print(f"❌ Channel with ID {BACKUP_CHANNEL_ID} not found.")
            return

        if MAIN_SERVER and (channel.guild is None or channel.guild.id != MAIN_SERVER):
            print(f"❌ Channel is not in the main server (expected {MAIN_SERVER}).")
            return

        if not attachments:
            print("❌ No files were backed up.")
            return

        try:
            status_msg = await channel.send(content="🕒 Automated backup is starting...")
        except Exception as e:
            print(f"❌ Failed to send backup start message: {e}")

        try:
            if status_msg:
                await status_msg.edit(content=f"🕒 Automated backup at `{timestamp}`", attachments=attachments)
            else:
                await channel.send(content=f"🕒 Automated backup at `{timestamp}`", files=attachments)
        except Exception as e:
            print(f"❌ Failed to send backup to channel: {e}")

    @commands.hybrid_command(name="backup", description="Backup .env, emojis.py, and PostgreSQL database and send to your DMs.")
    async def backup(self, ctx: commands.Context):
        if ctx.author.id not in BOT_OWNER_IDS:
            v = owner_design.permission_denied()
            if hasattr(ctx, "interaction") and ctx.interaction and not ctx.interaction.response.is_done():
                return await ctx.interaction.response.send_message(view=v, ephemeral=True)
            else:
                return await ctx.send(view=v)

        if hasattr(ctx, "interaction") and ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.interaction.response.defer(ephemeral=True)

        attachments, _ = await self.perform_backup()

        if attachments:
            try:
                await ctx.author.send(
                    content="✅ Here are your backup files:",
                    files=attachments
                )
                msg = "📬 Backup sent to your DMs!"
            except discord.Forbidden:
                msg = "❌ Couldn't send you a DM. Please enable DMs from server members."
        else:
            msg = "❌ No files were backed up."

        if hasattr(ctx, "interaction") and ctx.interaction:
            await ctx.interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx.send(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(BackupCog(bot))
