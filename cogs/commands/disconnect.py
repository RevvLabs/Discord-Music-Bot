import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.voice_connected import ensure_voice
from utils.embed_designs import disconnect as disconnect_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class disconnect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="disconnect", description="Disconnect the bot from the voice channel.", aliases=["dc"])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def disconnect(self, ctx: commands.Context):
        if not await ensure_voice(ctx):
            return
        if ctx.voice_client is None:
            return schedule_delete(await ctx.send(view=disconnect_design.not_connected()))

        schedule_delete(await ctx.send(view=disconnect_design.disconnected()))

        from utils.helper_function.autoplay_cache import autoplay_cache
        from cogs.commands.playlist import stop_playlist_session
        autoplay_cache.stop_session(ctx.guild.id)
        stop_playlist_session(ctx.guild.id)

        try:
            await ctx.voice_client.disconnect(force=True)
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(disconnect(bot))
