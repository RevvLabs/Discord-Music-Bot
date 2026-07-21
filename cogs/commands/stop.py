import discord
from discord.ext import commands
import voltricx
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from discord.ext.commands import BucketType
from utils.helper_function.voice_connected import ensure_voice
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import stop as stop_design
from utils.helper_function.auto_delete import schedule_delete

DEFAULT_VOLUME = 60


class Stop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="stop", description="Stops the music and leaves the voice channel.", aliases=['st'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def stop(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not await ensure_voice(ctx):
            return

        player: LavaMusic = ctx.guild.voice_client

        # Snapshot before stopping so we can display it
        track       = player.current
        track_title = track.title                          if track else None
        track_uri   = track.uri                            if track else None
        artwork_url = getattr(track, "artwork", None)      if track else None

        # Full reset — clear queue, stop autoplay, restore volume, reset filters
        from utils.helper_function.autoplay_cache import autoplay_cache
        from cogs.commands.playlist import stop_playlist_session
        autoplay_cache.stop_session(ctx.guild.id)
        stop_playlist_session(ctx.guild.id)
        player.queue.clear()
        player._autoplay     = voltricx.AutoPlayMode.partial   # autoplay has no setter
        player.filter_name   = "None"
        player.filter_status = False
        player.filters.reset()
        await player.set_volume(DEFAULT_VOLUME)
        await player.set_filters(player.filters)
        await player.stop()
        await player.disconnect()

        view = stop_design.stop_card(track_title, artwork_url, ctx.author.mention)
        schedule_delete(await ctx.send(view=view))

async def setup(bot) -> None:
    await bot.add_cog(Stop(bot))
