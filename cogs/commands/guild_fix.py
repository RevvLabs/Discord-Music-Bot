import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.voice_connected import ensure_voice
from utils.helper_function.setup_enforcer import enforce_setup
import voltricx
from voltricx.player import Player
from discord.ext.commands import BucketType
load_dotenv()
MAIN_SERVER = os.getenv("MAIN_SERVER")
BOT_OWNER_IDS = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]

from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import guild_fix as gf_design
from utils.helper_function.auto_delete import schedule_delete

class GuildFixCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="fix", description="Fixes the voice connection for this guild only.", aliases=["fx"])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def guildfix(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return 
        if not await ensure_voice(ctx):
            return
        try:
            player: Player = ctx.guild.voice_client
            if player:
                await player.disconnect()
                schedule_delete(await ctx.send(view=gf_design.connection_fixed()))
            else:
                schedule_delete(await ctx.send(view=gf_design.no_connection()))
        except Exception as e:
            print(e)
            schedule_delete(await ctx.send(view=gf_design.fix_error()))

async def setup(bot):
    await bot.add_cog(GuildFixCog(bot))
