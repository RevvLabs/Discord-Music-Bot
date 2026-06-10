import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.user_favorite import add_favorite
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import save_favorite as sf_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class SaveFavorite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="savefav",
        description="Save the currently playing song or all songs in the queue to your favorites.",
        aliases=["sf", "like", "save", "addfav", "af", "add"],
    )
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def savefav(self, ctx: commands.Context):
        player: LavaMusic = ctx.guild.voice_client
        if not player or (not player.current and not getattr(player, "queue", None)):
            schedule_delete(await ctx.send(view=sf_design.no_track()))
            return

        class SaveFavSelect(discord.ui.Select):
            def __init__(self, author_id):
                options = [
                    discord.SelectOption(label="Current Song",        value="current", description="Save the currently playing song"),
                    discord.SelectOption(label="All Songs in Queue",  value="all",     description="Save all songs in the queue (including current)"),
                ]
                super().__init__(placeholder="Choose what to save...", min_values=1, max_values=1, options=options)
                self.author_id = author_id

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != self.author_id:
                    await interaction.response.send_message("Only the command invoker can use this menu.", ephemeral=True)
                    return
                self.view.value = self.values[0]
                self.view.stop()
                await interaction.response.defer()

        class SaveFavView(discord.ui.LayoutView):
            def __init__(self, author_id, *, timeout=30):
                super().__init__(timeout=timeout)
                self.value = None
                self.add_item(sf_design.save_picker_container())
                self.row = discord.ui.ActionRow()
                self.row.add_item(SaveFavSelect(author_id))
                self.add_item(self.row)

        view = SaveFavView(ctx.author.id)
        prompt_msg = await ctx.send(view=view)
        await view.wait()

        choice = view.value
        try:
            await prompt_msg.delete()
        except Exception:
            pass

        if not choice:
            await ctx.send(view=sf_design.no_option_selected(), ephemeral=True)
            return

        if choice == "current":
            track = player.current
            if not track:
                schedule_delete(await ctx.send(view=sf_design.no_track_playing()))
                return
            await add_favorite(ctx.author.id, track.uri, track.title)
            schedule_delete(await ctx.send(view=sf_design.saved_current(track.title[:50], track.uri)))
        else:
            queue_tracks = []
            if player.current:
                queue_tracks.append(player.current)
            if hasattr(player, "queue"):
                queue_tracks.extend(list(player.queue))
            if not queue_tracks:
                schedule_delete(await ctx.send(view=sf_design.empty_queue()))
                return
            added = 0
            for track in queue_tracks:
                try:
                    await add_favorite(ctx.author.id, track.uri, track.title)
                    added += 1
                except Exception:
                    continue
            schedule_delete(await ctx.send(view=sf_design.saved_queue(added)))

async def setup(bot):
    await bot.add_cog(SaveFavorite(bot))
