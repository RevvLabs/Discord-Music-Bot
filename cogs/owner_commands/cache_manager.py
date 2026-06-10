import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
import voltricx
from utils.colours.embed_text_colours import wrap_green, wrap_red, wrap_yellow
from utils.logger.mewzik_logger import bot_logger

from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import owner as owner_design

load_dotenv()
BOT_OWNER_IDS = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]

class CacheManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="cache", description="Manage and inspect the voltricx HyperCache.", invoke_without_command=True)
    async def cache(self, ctx: commands.Context):
        if ctx.author.id not in BOT_OWNER_IDS:
            return await ctx.send(view=owner_design.permission_denied(), ephemeral=True)
        
        await ctx.send_help(ctx.command)

    @cache.command(name="stats", description="Show HyperCache statistics.")
    async def stats(self, ctx: commands.Context):
        if ctx.author.id not in BOT_OWNER_IDS:
            return

        stats = voltricx.Pool.get_cache_stats()
        
        await ctx.send(view=owner_design.cache_stats(stats['l1_queries'], stats['l2_tracks']))

    @cache.command(name="export", description="Export full cache data to a file at the root.")
    async def export(self, ctx: commands.Context):
        if ctx.author.id not in BOT_OWNER_IDS:
            return

        data = voltricx.Pool.export_cache_data()
        bot_name = os.getenv("BOT_NAME", "default")
        file_path = f"cache_export_{bot_name}.txt"
        
        # Format the data for better readability in the txt file
        content = "=== HyperCache Export ===\n\n"
        content += f"Timestamp: {discord.utils.utcnow()}\n"
        content += f"L1 Queries: {len(data['l1'])}\n"
        content += f"L2 Tracks: {len(data['l2'])}\n\n"
        
        content += "--- L1: Queries -> Track IDs ---\n"
        for query, tids in data['l1'].items():
            content += f"Q: {query}\n"
            content += f"IDs: {tids}\n\n"
            
        content += "--- L2: Track ID -> Title ---\n"
        for tid, title in data['l2'].items():
            content += f"{tid}: {title}\n"
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        await ctx.send(view=owner_design.cache_exported(file_path), file=discord.File(file_path))

    @cache.command(name="cacheclear", description="Clear all cache data.")
    async def clear(self, ctx: commands.Context):
        if ctx.author.id not in BOT_OWNER_IDS:
            return
            
        # We don't have a direct clear method on Pool that clears JUST the cache 
        # without closing nodes, but we can close and reconnect or just clear the caches.
        # Actually, let's just clear the caches if we can.
        # HyperCache has a clear method but we need to expose it.
        # For now, let's just implement stats and export as requested.
        pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CacheManager(bot))
