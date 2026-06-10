import discord
from discord.ext import commands
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.user_favorite import get_favorites, remove_favorite
from utils.helper_function.VoltricxPlayer import LavaMusic
import voltricx
import asyncio
from discord.ext.commands import BucketType
from dotenv import load_dotenv
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import favorites as fav_design
from utils.helper_function.auto_delete import schedule_delete
from emojis import PREV_BTN, NEXT_BTN, OPTIONS_BTN

load_dotenv()

currently_loading = set()


def _trunc(s: str, n: int = 30) -> str:
    """Truncate a string to n characters, appending … if cut."""
    return (s[:n - 1] + "…") if len(s) > n else s


async def add_favorites_to_queue(ctx, player, favorites, bot):
    """
    Resolve the first favorite immediately and start playback.
    Queue the rest in a background task so the user doesn't wait.
    Returns total number of favorites scheduled (0 if nothing resolved).
    """
    if not favorites:
        return 0

    # Phase 1: resolve and start the first resolvable track immediately
    first_track = None
    first_idx = 0
    for i, (url, title) in enumerate(favorites):
        try:
            tracks = await voltricx.Playable.search(url)
            if not tracks:
                continue
            t = tracks.tracks[0] if isinstance(tracks, voltricx.Playlist) else tracks[0]
            if t and (not hasattr(player, "check_queue_size") or player.check_queue_size()):
                player.metadata[t] = {"requestor": ctx.author, "source": t.source}
                player.queue.put(t)
                first_track = t
                first_idx = i
                break
        except Exception:
            continue

    if not first_track:
        return 0

    # Start playing immediately
    if not player.playing:
        try:
            next_track = player.queue.get()
            await player.play(next_track, replace=False)
        except Exception:
            pass
    if player.paused:
        await player.pause(False)

    # Phase 2: queue everything after the first track in the background
    remaining = favorites[first_idx + 1:]

    async def _bg_fill():
        for url, _title in remaining:
            if hasattr(player, "check_queue_size") and not player.check_queue_size():
                break
            try:
                tracks = await voltricx.Playable.search(url)
                if not tracks:
                    continue
                if isinstance(tracks, voltricx.Playlist):
                    for track in tracks.tracks[:100]:
                        if hasattr(player, "check_queue_size") and not player.check_queue_size():
                            break
                        player.metadata[track] = {"requestor": ctx.author, "source": track.source}
                        player.queue.put(track)
                        await asyncio.sleep(0.2)
                else:
                    t = tracks[0]
                    player.metadata[t] = {"requestor": ctx.author, "source": t.source}
                    player.queue.put(t)
                    await asyncio.sleep(0.2)
            except Exception:
                continue

    asyncio.create_task(_bg_fill())
    return len(favorites)


class RemoveFavoriteDropdown(discord.ui.Select):
    def __init__(self, parent_view, current_chunk):
        options = [
            discord.SelectOption(
                label=f"{parent_view.current_page * parent_view.chunk_size + idx + 1}. {title}",
                value=str(idx),
            )
            for idx, (url, title) in enumerate(current_chunk)
        ]
        super().__init__(
            placeholder="Remove favorite(s) from this page...",
            min_values=1,
            max_values=len(current_chunk),
            options=options,
        )
        self.parent_view = parent_view
        self.current_chunk = current_chunk

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.ctx_author:
            await interaction.response.send_message(view=fav_design.not_authorized(), ephemeral=True)
            return

        indices = sorted([int(i) for i in self.values], reverse=True)
        user_id = self.parent_view.ctx_author.id
        for idx in indices:
            url, _ = self.current_chunk[idx]
            await remove_favorite(user_id, url)
            self.current_chunk.pop(idx)
            global_index = self.parent_view.current_page * self.parent_view.chunk_size + idx
            self.parent_view.favorites.pop(global_index)
        self.parent_view.chunks = [
            self.parent_view.favorites[i:i + self.parent_view.chunk_size]
            for i in range(0, len(self.parent_view.favorites), self.parent_view.chunk_size)
        ]
        if self.parent_view.current_page >= len(self.parent_view.chunks):
            self.parent_view.current_page = max(0, len(self.parent_view.chunks) - 1)
        self.parent_view.update_buttons()
        await interaction.response.edit_message(view=self.parent_view)


class PlayBatchSelect(discord.ui.Select):
    """Lets the user pick a 100-song block from their full favorites list."""

    def __init__(self, parent_view):
        total = len(parent_view.favorites)
        options = []
        for start in range(0, min(total, 2500), 100):
            end = min(start + 100, total)
            options.append(
                discord.SelectOption(
                    label=f"#{start + 1} – #{end}",
                    value=str(start),
                    description=f"Queue songs {start + 1} to {end}",
                )
            )
        super().__init__(
            placeholder="Queue a block of 100 songs…",
            min_values=1,
            max_values=1,
            options=options[:25],
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.ctx_author:
            await interaction.response.send_message(view=fav_design.not_authorized(), ephemeral=True)
            return

        user_id = self.parent_view.ctx_author.id
        if user_id in currently_loading:
            await interaction.response.send_message(view=fav_design.currently_loading(), ephemeral=True)
            return

        start = int(self.values[0])
        end = min(start + 100, len(self.parent_view.favorites))
        batch = self.parent_view.favorites[start:end]

        currently_loading.add(user_id)
        try:
            await interaction.response.edit_message(view=fav_design.favorites_loading())

            ctx = self.parent_view.ctx
            user = ctx.author

            player = ctx.guild.voice_client
            if not player:
                try:
                    await voltricx.Pool.wait_until_ready()
                except AttributeError:
                    pass
                channel = user.voice.channel
                player = await channel.connect(cls=LavaMusic, timeout=45, reconnect=True, self_deaf=True)
                player.home = ctx.channel

            if not isinstance(player.queue, voltricx.Queue):
                player.queue = voltricx.Queue()
            if not getattr(player, "home", None):
                player.home = ctx.channel

            added = await add_favorites_to_queue(ctx, player, batch, ctx.bot)

            if added == 0:
                await interaction.followup.send(view=fav_design.no_valid_favorites(), ephemeral=True)
            else:
                await interaction.followup.send(
                    view=fav_design.batch_queued(start + 1, end, added),
                    ephemeral=True,
                )

            self.parent_view.update_buttons()
            await interaction.message.edit(view=self.parent_view)

        except Exception as e:
            print(f"[PlayBatchSelect] Error: {e}")
        finally:
            currently_loading.discard(user_id)


class PlayFavoriteDropdown(discord.ui.Select):
    def __init__(self, parent_view, current_chunk):
        options = [
            discord.SelectOption(
                label=f"{parent_view.current_page * parent_view.chunk_size + idx + 1}. {_trunc(title)}",
                value=str(idx),
            )
            for idx, (url, title) in enumerate(current_chunk)
        ]
        super().__init__(
            placeholder="Play favorite(s) from this page...",
            min_values=1,
            max_values=len(current_chunk),
            options=options,
        )
        self.parent_view = parent_view
        self.current_chunk = current_chunk

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.ctx_author:
            await interaction.response.send_message(view=fav_design.not_authorized(), ephemeral=True)
            return

        user_id = self.parent_view.ctx_author.id
        if user_id in currently_loading:
            await interaction.response.send_message(view=fav_design.currently_loading(), ephemeral=True)
            return

        currently_loading.add(user_id)
        try:
            await interaction.response.edit_message(view=fav_design.favorites_loading())

            indices = sorted([int(i) for i in self.values])
            selected_favorites = [self.current_chunk[idx] for idx in indices]

            ctx = self.parent_view.ctx
            bot = ctx.bot
            user = ctx.author

            player = ctx.guild.voice_client
            if not player:
                try:
                    await voltricx.Pool.wait_until_ready()
                except AttributeError:
                    pass
                channel = user.voice.channel
                player = await channel.connect(cls=LavaMusic, timeout=45, reconnect=True, self_deaf=True)
                player.home = ctx.channel

            if not isinstance(player.queue, voltricx.Queue):
                player.queue = voltricx.Queue()
            if not getattr(player, "home", None):
                player.home = ctx.channel

            added = await add_favorites_to_queue(ctx, player, selected_favorites, bot)

            if added == 0:
                await interaction.followup.send(view=fav_design.no_valid_favorites(), ephemeral=True)
            else:
                await interaction.followup.send(view=fav_design.favorites_added(added), ephemeral=True)

            self.parent_view.update_buttons()
            await interaction.message.edit(view=self.parent_view)

        except Exception as e:
            print(f"[PlayFavoriteDropdown] Error: {e}")
        finally:
            currently_loading.discard(user_id)


class PaginationView(discord.ui.LayoutView):
    def __init__(self, favorites, create_embed_fn, ctx=None, interaction=None, criteria_callback=None, current_page=0):
        super().__init__(timeout=60.0)
        self.favorites = favorites
        self.chunk_size = 20
        self.chunks = [favorites[i:i + self.chunk_size] for i in range(0, len(favorites), self.chunk_size)]
        self.create_embed_fn = create_embed_fn
        self.current_page = current_page

        self.ctx = ctx
        self.ctx_author = interaction.user if interaction else ctx.author
        self.criteria_callback = criteria_callback

        self.navigation_row = discord.ui.ActionRow()
        self.play_dropdown_row = discord.ui.ActionRow()
        self.dropdown_row = discord.ui.ActionRow()
        self.action_row = discord.ui.ActionRow()

        self.prev_button = discord.ui.Button(label="Previous", emoji=PREV_BTN, style=discord.ButtonStyle.secondary)
        self.next_button = discord.ui.Button(label="Next", emoji=NEXT_BTN, style=discord.ButtonStyle.secondary)
        self.play_all_button = discord.ui.Button(label="Play All", style=discord.ButtonStyle.success)
        self.close_button = discord.ui.Button(label="Close List", style=discord.ButtonStyle.danger)

        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page
        self.play_all_button.callback = self.play_all
        self.close_button.callback = self.close_list

        self.update_buttons()
        self.message = None

    def update_buttons(self):
        self.prev_button.disabled = self.current_page <= 0
        self.next_button.disabled = self.current_page >= len(self.chunks) - 1

        self.clear_items()
        self.navigation_row.clear_items()
        self.play_dropdown_row.clear_items()
        self.dropdown_row.clear_items()
        self.action_row.clear_items()

        data = self.create_embed_fn(self)
        header_text = f"## {data['title']}" if data.get('title') else "### Favorites"
        content_text = data.get('description') or "No favorites found."
        container = discord.ui.Container(
            discord.ui.TextDisplay(content=header_text),
            discord.ui.TextDisplay(content=content_text),
            accent_color=EMBED_COLOR,
        )
        self.add_item(container)

        self.navigation_row.add_item(self.prev_button)
        self.navigation_row.add_item(self.next_button)

        if self.chunks:
            self.play_dropdown_row.add_item(PlayFavoriteDropdown(self, self.chunks[self.current_page]))
            self.dropdown_row.add_item(RemoveFavoriteDropdown(self, self.chunks[self.current_page]))

        self.action_row.add_item(self.play_all_button)
        self.action_row.add_item(self.close_button)

        if self.criteria_callback:
            criteria_button = discord.ui.Button(label="Change Criteria", emoji=OPTIONS_BTN, style=discord.ButtonStyle.primary)
            criteria_button.callback = self.criteria_callback
            self.action_row.add_item(criteria_button)

        self.add_item(self.navigation_row)
        if self.chunks:
            self.add_item(self.play_dropdown_row)
            self.add_item(self.dropdown_row)
        self.add_item(self.action_row)

        if len(self.favorites) > 100:
            batch_row = discord.ui.ActionRow()
            batch_row.add_item(PlayBatchSelect(self))
            self.add_item(batch_row)

    async def play_all(self, interaction: discord.Interaction):
        user_id = self.ctx_author.id
        if interaction.user != self.ctx_author:
            await interaction.response.send_message(view=fav_design.not_authorized(), ephemeral=True)
            return
        if user_id in currently_loading:
            await interaction.response.send_message(view=fav_design.currently_loading(), ephemeral=True)
            return

        currently_loading.add(user_id)
        try:
            await interaction.response.edit_message(view=fav_design.favorites_loading())

            ctx = self.ctx
            bot = ctx.bot
            user = ctx.author

            player = ctx.guild.voice_client
            if not player:
                try:
                    await voltricx.Pool.wait_until_ready()
                except AttributeError:
                    pass
                channel = user.voice.channel
                player = await channel.connect(cls=LavaMusic, timeout=45, reconnect=True, self_deaf=True)
                player.home = ctx.channel

            if not isinstance(player.queue, voltricx.Queue):
                player.queue = voltricx.Queue()
            if not getattr(player, "home", None):
                player.home = ctx.channel

            added = await add_favorites_to_queue(ctx, player, self.favorites, bot)

            if added == 0:
                await interaction.followup.send(view=fav_design.no_valid_tracks_play_all(), ephemeral=True)
                return

            await interaction.followup.send(view=fav_design.favorites_added(added), ephemeral=True)
        finally:
            currently_loading.discard(user_id)

    async def close_list(self, interaction: discord.Interaction):
        if interaction.user != self.ctx_author:
            await interaction.response.send_message(view=fav_design.not_authorized(), ephemeral=True)
            return
        await interaction.response.edit_message(view=fav_design.favorites_closed())

    async def on_timeout(self):
        if self.message:
            try:
                v = discord.ui.LayoutView()
                v.add_item(discord.ui.Container(
                    discord.ui.TextDisplay(content="⏳ Closed — inactive for too long."),
                    accent_color=discord.Color.from_rgb(128, 128, 128),
                ))
                await self.message.edit(view=v)
            except Exception:
                pass

    async def prev_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx_author:
            await interaction.response.send_message(view=fav_design.not_authorized(), ephemeral=True)
            return
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx_author:
            await interaction.response.send_message(view=fav_design.not_authorized(), ephemeral=True)
            return
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(view=self)

    def create_embed(self):
        return self.create_embed_fn(self)


class ListFavorites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="favorite", description="List your favorite songs.", aliases=["fav", "f", "favorites"])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def listfav(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        user_id = ctx.author.id
        if user_id in currently_loading:
            await ctx.send(view=fav_design.currently_loading(), ephemeral=True)
            return

        favorites = await get_favorites(user_id)
        if not favorites:
            schedule_delete(await ctx.send(view=fav_design.no_favorites_saved()))
            return

        def create_embed(view: PaginationView):
            if not view.chunks:
                desc = "You have no favorite songs saved."
            else:
                current_chunk = view.chunks[view.current_page]
                desc = "\n".join([
                    f"**#{idx + view.current_page * view.chunk_size + 1} - [{_trunc(title)}]({url})**"
                    for idx, (url, title) in enumerate(current_chunk)
                ])
            return {
                'title': f"Your Favorite Songs (Page {view.current_page + 1}/{max(1, len(view.chunks))})",
                'description': desc,
            }

        view = PaginationView(favorites, create_embed, ctx=ctx)
        msg = await ctx.send(view=view)
        view.message = msg


async def setup(bot):
    await bot.add_cog(ListFavorites(bot))
