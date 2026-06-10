import discord
from discord.ext import commands
import voltricx

from utils.colours.embed_text_colours import wrap_green, wrap_red
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import owner as owner_design

import os
from dotenv import load_dotenv
load_dotenv()
BOT_OWNER_IDS = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]

class ConfirmModal(discord.ui.Modal, title="Confirmation Required"):
    confirm_input = discord.ui.TextInput(
        label="Type 'confirm' to proceed",
        placeholder="Type here...",
        style=discord.TextStyle.short,
        required=True,
        max_length=20
    )

    def __init__(self):
        super().__init__(timeout=30)
        self.confirmed = False

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm_input.value.strip().lower() == "confirm":
            self.confirmed = True
            await interaction.response.send_message("Confirmed. Showing node info...", ephemeral=True)
        else:
            await interaction.response.send_message("You must type 'confirm' to proceed.", ephemeral=True)

class LavalinkNodeInfo(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="realnode", description="Display detailed information about Lavalink nodes.")
    async def node(self, ctx: commands.Context):
        if ctx.author.id not in BOT_OWNER_IDS:
            return await ctx.send(view=owner_design.permission_denied())

        if ctx.interaction:
            modal = ConfirmModal()
            await ctx.interaction.response.send_modal(modal)
            try:
                await modal.wait()
            except Exception:
                pass
            if not modal.confirmed:
                await ctx.send(view=owner_design.no_confirmation())
                return
        elif ctx.message:
            confirm_msg = await ctx.send("Type `confirm` to proceed (30s timeout):")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            import asyncio
            try:
                reply = await ctx.bot.wait_for("message", check=check, timeout=30)
                await confirm_msg.delete()
                if reply.content.strip().lower() != "confirm":
                    return await ctx.send(view=owner_design.cancelled())
            except asyncio.TimeoutError:
                return await ctx.send(view=owner_design.timed_out())

        if not voltricx.Pool.nodes():
            await ctx.send(view=owner_design.no_nodes())
            return

        nodes = list(voltricx.Pool.nodes().values())
        from datetime import datetime

        for idx, node in enumerate(nodes, start=1):
            try:
                stats = await node.fetch_stats()
                player_info = await node.fetch_info()

                dt = datetime.fromtimestamp(player_info.build_time / 1000)
                build_time = dt.strftime("%B %d, %Y at %I:%M:%S %p UTC")

                uptime_ms = stats.get("uptime", 0)
                uptime_seconds = uptime_ms // 1000
                days = uptime_seconds // 86400
                hours = (uptime_seconds % 86400) // 3600
                minutes = (uptime_seconds % 3600) // 60

                memory = stats.get("memory", {})
                cpu = stats.get("cpu", {})

                title = f"Lavalink Node Stats — Node {idx}/{len(nodes)}"
                status_text = (wrap_green('CONNECTED') if node.status == voltricx.NodeStatus.connected else wrap_red('DISCONNECTED'))

                node_info = (
                    f"Identifier: || {node.identifier} ||\n"
                    f"Node Ip :  || {node.uri} ||\n"
                    f"Password : || {node.config.password} ||\n"
                    f"Status : ` {node.status.value} `\n"
                    f"Heartbeat : ` {node.config.heartbeat} sec `\n"
                    f"Session ID : || {node.session_id} ||"
                )

                lavalink_stats = (
                    f"Uptime: ` {days}d {hours}h {minutes}m `\n"
                    f"Players: ` {stats.get('players', 0)} `\n"
                    f"Playing: ` {stats.get('playingPlayers', 0)} `"
                )

                memory_usage = (
                    f"Used : ` {memory.get('used', 0) / 1024 / 1024:.2f} MB `\n"
                    f"Free : ` {memory.get('free', 0) / 1024 / 1024:.2f} MB `\n"
                    f"Allocated : ` {memory.get('allocated', 0) / 1024 / 1024:.2f} MB `\n"
                    f"Reservable : ` {memory.get('reservable', 0) / 1024 / 1024:.2f} MB `"
                )

                cpu_stats = (
                    f"Cores : ` {cpu.get('cores', 0)} `\n"
                    f"Lavalink Load : ` {cpu.get('lavalinkLoad', 0):.2f} `\n"
                    f"System Load : ` {cpu.get('systemLoad', 0):.2f} `"
                )

                player_info_text = (
                    f"LavaPlayer : ` {player_info.lavaplayer} `\n"
                    f"Build Time : ` {build_time} `\n"
                    f"Version : ` {player_info.version.semver} `\n"
                    f"Major : ` {player_info.version.major} `\n"
                    f"Minor : ` {player_info.version.minor} `\n"
                    f"Patch : ` {player_info.version.patch} `\n"
                    f"Build : ` {player_info.version.build} `"
                )

                container = discord.ui.Container(
                    discord.ui.TextDisplay(content=f"## {title}\n{status_text}"),
                    discord.ui.TextDisplay(content=f"### Node Info\n{node_info}"),
                    discord.ui.TextDisplay(content=f"### Lavalink Stats\n{lavalink_stats}"),
                    discord.ui.TextDisplay(content=f"### Memory Usage\n{memory_usage}"),
                    discord.ui.TextDisplay(content=f"### CPU Stats\n{cpu_stats}"),
                    discord.ui.TextDisplay(content=f"### Player Info\n{player_info_text}"),
                    accent_color=EMBED_COLOR,
                )

                view = discord.ui.LayoutView()
                view.add_item(container)
                await ctx.send(view=view)

            except Exception as e:
                await ctx.send(view=owner_design.node_error(idx, str(e)))

async def setup(bot: commands.Bot):
    await bot.add_cog(LavalinkNodeInfo(bot))
