import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()

from utils.embed_designs import owner as owner_design

def is_bot_owner(user_id):
    owners = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]
    return user_id in owners

class Visualiser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="visualiser", description="Visualize all available owner commands and their status.")
    async def visualiser(self, ctx: commands.Context):
        if not is_bot_owner(ctx.author.id):
            await ctx.send(view=owner_design.permission_denied(), ephemeral=True)
            return

        # Get all commands in the owner_commands cog category or directory
        owner_commands_list = []
        owner_cogs = [
            'Dev', 'NoPrefix', 'ForceFix', 'RealNode', 'Partner', 'ShowNode', 
            'EngineControl', 'GeneratePremium', 'Backup', 'Blacklist', 
            'Bot247', 'BotChannelStatus', 'Broadcaster', 'CacheManager', 
            'ControllerManager', 'DebugBot', 'Maintenance', 'ValidateLicenseCogs'
        ]

        description = "### 🛠️ Owner Command Visualiser\n"
        description += "Below is a list of all owner-only commands available in the system.\n\n"

        for cog_name in sorted(owner_cogs):
            cog = self.bot.get_cog(cog_name)
            if cog:
                description += f"**{cog_name}**\n"
                cmd_list = []
                for cmd in cog.get_commands():
                    cmd_list.append(f"• `{cmd.name}`: {cmd.description}")
                description += "\n".join(cmd_list) + "\n\n"

        description += "--- \nAlways ephemeral | Use /help for all commands"

        await ctx.send(view=owner_design.visualiser_panel(description), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Visualiser(bot))
