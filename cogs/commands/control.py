import discord
from discord.ext import commands
from discord.ui import Button
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.admin_or_owner import admin_or_owner
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.unified_cache_manager import unified_cache
from discord.ext.commands import BucketType
from emojis import PREV, NEXT, STOP, PLAY, PAUSE, SETTINGS

from utils.helper_function.VoltricxPlayer import LavaMusic
from dotenv import load_dotenv
load_dotenv()

from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import control as ctrl_design
from utils.helper_function.auto_delete import schedule_delete


class Controls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Define the buttons
        self.previous_button = Button(emoji=PREV, style=discord.ButtonStyle.secondary, custom_id="previous")
        self.next_button = Button(emoji=NEXT, style=discord.ButtonStyle.secondary, custom_id="next")
        self.disconnect_button = Button(emoji=STOP, style=discord.ButtonStyle.danger, custom_id="disconnect")
        self.play_button = Button(emoji=PLAY, style=discord.ButtonStyle.secondary, custom_id="resume")
        self.pause_button = Button(emoji=PAUSE, style=discord.ButtonStyle.secondary, custom_id="pause")
        self.settings_button = Button(emoji=SETTINGS, style=discord.ButtonStyle.secondary, custom_id="settings")
        
    async def _get_controls_status(self, guild_id: int) -> bool:
        return await unified_cache.is_hide_controls_enabled(guild_id, self.bot.user.id)

    async def _update_controls_in_db(self, guild_id: int, hide: bool):
        await unified_cache.set_hide_controls(guild_id, self.bot.user.id, hide)

    @commands.hybrid_command(name="button", description="Toggle the visibility of the music control buttons.", aliases=['btn'])
    @admin_or_owner()
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def toggle_controls(self, ctx: commands.Context):
        try:
            if not await enforce_setup(ctx, EMBED_COLOR):
                return 
            player: LavaMusic = ctx.guild.voice_client
            current_status = await self._get_controls_status(ctx.guild.id)
            new_status = not current_status
            await self._update_controls_in_db(ctx.guild.id, new_status)
            
            
            message_text = "The music control buttons have been hidden." if new_status else "The music control buttons have been restored."
            
            if player and player.playing :
                controls_view = discord.ui.LayoutView()
                row = discord.ui.ActionRow()
                if new_status:
                    row.add_item(self.settings_button)
                else:
                    row.add_item(self.previous_button)
                    row.add_item(self.pause_button)
                    row.add_item(self.next_button)
                    row.add_item(self.disconnect_button)
                    row.add_item(self.settings_button)
                
                controls_view.add_item(row)

                if hasattr(ctx.guild.voice_client, 'msg'):
                    await ctx.guild.voice_client.msg.edit(view=controls_view)
            
            schedule_delete(await ctx.send(view=ctrl_design.controls_updated(message_text)))
        except Exception as e:
            print(f"Error in toggle_controls: {e}")
            schedule_delete(await ctx.send("An error occurred while toggling the controls."))

async def setup(bot):
    await bot.add_cog(Controls(bot))
