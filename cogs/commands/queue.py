import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.voice_connected import ensure_voice
from utils.helper_function.pagination import PaginationView
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import queue as queue_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="queue", description="Displays the current song queue.", aliases=['q'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def queue(self, ctx: commands.Context):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not await ensure_voice(ctx):
            return

        try:
            player: LavaMusic = ctx.guild.voice_client
            if not player or not player.queue:
                schedule_delete(await ctx.send(view=queue_design.empty_queue()))
                return

            chunk_size = 10
            chunks = [player.queue[i:i + chunk_size] for i in range(0, len(player.queue), chunk_size)]

            def create_embed(view: PaginationView):
                current_chunk = chunks[view.current_page]
                container_items = []

                header_text = f"## Songs In Queue (Page {view.current_page + 1}/{len(chunks)})\n"
                container_items.append(discord.ui.TextDisplay(content=header_text))

                for idx, track in enumerate(current_chunk, start=1):
                    track_index = idx + (view.current_page * chunk_size)

                    duration_ms = getattr(track, 'length', 0)
                    minutes, seconds = divmod(duration_ms // 1000, 60)
                    formatted_duration = f"{minutes:02}m {seconds:02}s"

                    requestor = "Unknown"
                    if hasattr(player, "metadata") and track in player.metadata:
                        req_obj = player.metadata[track].get("requestor", "Unknown")
                        requestor = req_obj.display_name if hasattr(req_obj, "display_name") else req_obj

                    title = getattr(track, 'title', 'Unknown Title')
                    uri   = getattr(track, 'uri', None)
                    author = getattr(track, 'author', 'Unknown Artist')

                    title_str = str(title)
                    if len(title_str) > 50:
                        title_str = title_str[:47] + "..."
                    track_info_content = (
                        f"**{track_index} - [{title_str}]({uri})**\n"
                        f"Artist : **{author}**\n"
                        f"Time   : **{formatted_duration}**\n"
                        f"Req. by: **{requestor}**"
                    )

                    container_items.append(discord.ui.TextDisplay(content=track_info_content))

                    if idx < len(current_chunk):
                        container_items.append(
                            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
                        )

                return container_items

            view = PaginationView(chunks, create_embed, ctx=ctx)
            msg = await ctx.send(view=view)
            view.message = msg
        except Exception as e:
            schedule_delete(await ctx.send(view=queue_design.error(str(e))))


async def setup(bot) -> None:
    await bot.add_cog(Queue(bot))
