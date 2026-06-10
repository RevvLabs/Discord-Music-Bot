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
from utils.helper_function.queue_placement import QueuePlacementView
from utils.embed_designs import search as search_design
from utils.helper_function.auto_delete import schedule_delete
import os
from dotenv import load_dotenv

load_dotenv()
BOT_NAME = os.getenv("BOT_NAME")


def _source_emoji(source_id: str, track_source: str, emoji_map: dict) -> str | None:
    """Return the matching platform emoji for a track source string."""
    s_id = source_id.lower()
    t_src = track_source.lower()
    
    # Priority 1: Use the engine ID used to find the track
    if "ytmsearch" in s_id: return emoji_map["ytmusic"]
    if "dzsearch"  in s_id: return emoji_map["deezer"]
    if "spsearch"  in s_id: return emoji_map["spotify"]
    if "jssearch"  in s_id: return emoji_map["jiosaavn"]
    if "scsearch"  in s_id: return emoji_map["soundcloud"]
    if "ytsearch"  in s_id: return emoji_map["youtube"]
    if "amsearch"  in s_id: return emoji_map["apple_music"]
    if "ytdl"      in s_id: return emoji_map["ytdlp"]
    
    # Priority 2: Fallback to track's internal source name
    if "youtube" in t_src:
        return emoji_map["ytmusic"] if "music" in t_src else emoji_map["youtube"]
    if "spotify" in t_src: return emoji_map["spotify"]
    if "jiosaavn" in t_src or "js" in t_src: return emoji_map["jiosaavn"]
    if "soundcloud" in t_src: return emoji_map["soundcloud"]
    if "deezer" in t_src or "dz" in t_src: return emoji_map["deezer"]
    if "apple" in t_src: return emoji_map["apple_music"]
    if "ytdl" in t_src: return emoji_map["ytdlp"]
    return None



class Search(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="search",
        description="Search for a song across multiple sources",
        aliases=["s"],
    )
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def search(self, ctx: commands.Context, *, query: str):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not await ensure_voice(ctx):
            return

        player: LavaMusic = ctx.guild.voice_client

        if not hasattr(player, "queue") or not isinstance(player.queue, voltricx.Queue):
            player.queue = voltricx.Queue()

        # BUG FIX 1: `Player.__init__` always sets `self.home = None`, so
        # `hasattr` was always True and home was never assigned.
        # Use a truthiness check instead so None is treated as "not set".
        if not player.home:
            player.home = ctx.channel

        from utils.helper_function.unified_cache_manager import unified_cache
        from emojis import JIOSAAVN, SPOTIFY, YTMUSIC, SOUNDCLOUD, DEEZER, YOUTUBE, APPLE_MUSIC, YTDLP

        emoji_map = {
            "youtube": YOUTUBE, "ytmusic": YTMUSIC, "spotify": SPOTIFY,
            "jiosaavn": JIOSAAVN, "soundcloud": SOUNDCLOUD, "deezer": DEEZER,
            "apple_music": APPLE_MUSIC, "ytdlp": YTDLP,
        }

        # Define engines with their IDs, names, and emojis
        engines = {
            "ytsearch": ("YouTube", YOUTUBE),
            "dzsearch": ("Deezer", DEEZER),
            "ytmsearch": ("YouTube Music", YTMUSIC),
            "spsearch": ("Spotify", SPOTIFY),
            "jssearch": ("JioSaavn", JIOSAAVN),
            "scsearch": ("SoundCloud", SOUNDCLOUD),
            "amsearch": ("Apple Music", APPLE_MUSIC),
            "ytdl": ("YouTube DL", YTDLP),
        }

        search_sources, emoji_list = [], []
        for engine_id, (engine_name, engine_emoji) in engines.items():
            if await unified_cache.is_engine_enabled(engine_id):
                search_sources.append(engine_id)
                emoji_list.append(engine_emoji)

        message = await ctx.reply(view=search_design.searching(ctx.author.mention, query))
        schedule_delete(message, 120)

        # -- fetch tracks from all enabled sources --
        all_results: list[tuple[voltricx.Playable, str]] = []  # (track, source_id)
        for source in search_sources:
            try:
                results = await voltricx.Playable.search(query, source=source)
                tracks = results.tracks if isinstance(results, voltricx.Playlist) else results or []
            except voltricx.LavalinkLoadException:
                continue
            except Exception as e:
                print(f"[Search] {source}: {e}")
                continue

            if tracks:
                for t in tracks[:4]:
                    all_results.append((t, source))
                if len(all_results) >= 20:
                    break

        if not all_results:
            await message.edit(view=search_design.no_results(ctx.author.mention, query))
            schedule_delete(message)
            return

        # -- build select options --
        options: list[discord.SelectOption] = []
        for i, (track, source_id) in enumerate(all_results):
            emoji = _source_emoji(source_id, track.source, emoji_map)
            if not emoji:
                emoji = emoji_list[(i // 4) % len(emoji_list)] if emoji_list else None

            engine_name = engines.get(source_id, (track.source, None))[0]
            options.append(
                discord.SelectOption(
                    label=f"{track.title[:50]} — {track.author[:28]}",
                    value=str(i),
                    description=f"{track.length // 60000}m {track.length // 1000 % 60}s · {engine_name}",
                    emoji=emoji,
                )
            )

        select_menu = discord.ui.Select(
            placeholder="🎵  Choose a track to play…",
            min_values=1,
            max_values=1,
            options=options,
        )

        command_user_id = ctx.author.id

        # ── select callback ────────────────────────────────────────────────────
        async def select_callback(interaction: discord.Interaction):
            if interaction.user.id != command_user_id:
                return await interaction.response.send_message(view=search_design.not_authorized(), ephemeral=True)

            # BUG FIX 2: Always acknowledge the interaction first.
            # Without this Discord shows "This interaction failed" regardless
            # of what the bot does next with the message.
            await interaction.response.defer()

            selected_index = int(select_menu.values[0])
            selected_track, selected_source = all_results[selected_index]

            player: LavaMusic = interaction.guild.voice_client
            if not player:
                return await interaction.followup.send(view=search_design.bot_disconnected(), ephemeral=True)

            if not player.check_queue_size():
                return await interaction.message.edit(view=search_design.queue_full(interaction.user.mention))

            if not hasattr(player, "metadata"):
                player.metadata = {}

            # Ensure home is set so on_voltricx_track_start can send the player card
            if not player.home:
                player.home = ctx.channel

            engine_name = engines.get(selected_source, (selected_track.source, None))[0]
            minutes, seconds = divmod((selected_track.length or 0) // 1000, 60)
            duration_str = f"{minutes:02}m {seconds:02}s"

            # ── Something already playing → ask where to place the track ──
            if player.playing:
                select_menu.disabled = True
                view.stop()
                placement = QueuePlacementView(
                    player=player,
                    track=selected_track,
                    requestor=interaction.user,
                    duration=duration_str,
                    source=selected_track.source,
                )
                placement.message = interaction.message
                await interaction.message.edit(view=placement)
                return

            # ── Nothing playing → queue and start immediately ──
            player.metadata[selected_track] = {
                "requestor": interaction.user,
                "source": selected_track.source,
            }
            player.queue.put(selected_track)

            if player.paused:
                await player.pause(False)

            if not player.playing:
                next_track = player.queue.get()
                await player.play(next_track, replace=True)

            # Disable the select so it can't be reused
            select_menu.disabled = True
            view.stop()

            confirmation = search_design.track_selected(
                track_title=selected_track.title,
                track_uri=selected_track.uri,
                author=selected_track.author,
                duration=duration_str,
                source=engine_name,
                requester_name=interaction.user.display_name,
                is_playing_now=True,
                artwork_url=getattr(selected_track, "artwork", None),
            )
            await interaction.message.edit(view=confirmation)

        select_menu.callback = select_callback

        first_artwork = next(
            (getattr(t, "artwork", None) for t, _ in all_results if getattr(t, "artwork", None)), None
        )
        view = search_design.search_results(
            query=query,
            result_count=len(all_results),
            user_mention=ctx.author.mention,
            artwork_url=first_artwork,
            select_menu=select_menu,
        )

        async def on_timeout():
            try:
                await message.delete()
            except discord.HTTPException:
                pass

        view.on_timeout = on_timeout
        view.timeout = 60

        await message.edit(view=view)


async def setup(bot):
    await bot.add_cog(Search(bot))
