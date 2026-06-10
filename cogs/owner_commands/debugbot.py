import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import voltricx
from voltricx import voltricx_logger
from utils.colours.embed_text_colours import wrap_green, wrap_red
from utils.logger.mewzik_logger import bot_logger

from utils.embed_designs import owner as owner_design

load_dotenv()
BOT_OWNER_IDS = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]


class DebugBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="debugbot",
        description="Toggle detailed voltricx debug logging on or off.",
    )
    async def debugbot(self, ctx: commands.Context) -> None:
        if ctx.author.id not in BOT_OWNER_IDS:
            return await ctx.send(view=owner_design.permission_denied(), ephemeral=True)

        new_state: bool = voltricx_logger.toggle()

        if bot_logger.enabled:
            bot_logger.info(
                "/debugbot toggled",
                user_id=ctx.author.id,
                user=str(ctx.author),
                voltricx_debug=new_state,
            )

        node_count = len(voltricx.Pool.nodes())
        await ctx.send(view=owner_design.debug_toggle(new_state, node_count), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DebugBot(bot))
