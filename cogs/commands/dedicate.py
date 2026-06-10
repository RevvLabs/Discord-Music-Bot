import discord
from discord.ext import commands
import voltricx
from utils.helper_function.unified_cache_manager import unified_cache
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.dj_checker import dj_lockable
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.VoltricxPlayer import LavaMusic
from discord.ext.commands import BucketType
import os
from dotenv import load_dotenv
from utils.helper_function.bot_config import EMBED_COLOR
from utils.helper_function.queue_placement import QueuePlacementView
from utils.embed_designs import dedicate as dedicate_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


class Dedicate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_voice(self, ctx):
        user = ctx.author
        if not user.voice or not user.voice.channel:
            await ctx.send(view=dedicate_design.not_in_voice(), ephemeral=True)
            return False

        voice_client = ctx.guild.voice_client
        if not voice_client:
            channel = user.voice.channel
            player: LavaMusic = await channel.connect(cls=LavaMusic)
            schedule_delete(await ctx.send(view=dedicate_design.joined_voice(channel.name)))
            player.home = ctx.channel
            return True
        elif voice_client.channel != user.voice.channel:
            await ctx.send(view=dedicate_design.different_voice(), ephemeral=True)
            return False

        return True

    async def get_user_engine(self, user_id):
        try:
            return await unified_cache.get_user_engine(user_id)
        except Exception:
            return None

    @commands.hybrid_command(name="dedicate", description="Dedicate a song to a user. Usage: /dedicate @user <song name>", aliases=["d"])
    @commands.cooldown(1, 2, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    @dj_lockable()
    async def dedicate(self, ctx: commands.Context, user: discord.Member, *, song_name: str):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not await self.ensure_voice(ctx):
            return

        player: LavaMusic = ctx.guild.voice_client

        if not isinstance(player.queue, voltricx.Queue):
            player.queue = voltricx.Queue()

        if not getattr(player, "home", None):
            player.home = ctx.channel

        user_engine = await self.get_user_engine(ctx.author.id) or "ytsearch"

        search_sources = [user_engine, "ytsearch", "dzsearch", "ytmsearch", "spsearch", "jssearch", "scsearch", "amsearch", "ytdl"]
        seen = set()
        unique_sources = [s for s in search_sources if not (s in seen or seen.add(s))]

        tracks = None
        for source in unique_sources:
            try:
                tracks = await voltricx.Playable.search(song_name, source=source)
                if tracks:
                    player.source = source
                    break
            except voltricx.LavalinkLoadException:
                continue
            except Exception as e:
                print(f"[DEBUG] Dedicate search error for {source}: {e}")
                continue

        if not tracks:
            await ctx.send(view=dedicate_design.no_results(song_name), ephemeral=True)
            return

        track: voltricx.Playable = tracks[0]

        if not player.check_queue_size():
            await ctx.send(view=dedicate_design.queue_full(), ephemeral=True)
            return

        view = dedicate_design.dedication_card(
            track=track,
            from_user=ctx.author,
            to_user=user,
        )
        schedule_delete(await ctx.send(view=view))

        duration_ms = track.length or 0
        mins, secs = divmod(duration_ms // 1000, 60)
        formatted_duration = f"{mins:02}m {secs:02}s"

        # ── Something already playing → let the dedicator choose placement ──
        if player.playing:
            placement = QueuePlacementView(
                player=player,
                track=track,
                requestor=ctx.author,
                duration=formatted_duration,
                source=track.source,
            )
            placement.message = await ctx.send(view=placement, ephemeral=True)
            return

        # ── Nothing playing → queue and start immediately ──
        player.metadata[track] = {"requestor": ctx.author, "source": track.source}
        player.queue.put(track)
        if player.paused:
            await player.pause(False)

        if not player.playing:
            next_track = player.queue.get()
            await player.play(next_track, replace=True)

async def setup(bot):
    await bot.add_cog(Dedicate(bot))
