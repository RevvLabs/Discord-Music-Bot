import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from utils.helper_function.unified_cache_manager import unified_cache
from utils.helper_function.bot_config import EMBED_COLOR
from emojis import JIOSAAVN, SPOTIFY, YTMUSIC, SOUNDCLOUD, YOUTUBE, DEEZER, APPLE_MUSIC, YTDLP
from utils.embed_designs import owner as owner_design

load_dotenv()

def is_bot_owner(user_id):
    owners = [int(x.strip()) for x in os.getenv("BOT_OWNER_IDS", "").split(",") if x.strip()]
    return user_id in owners

class EngineMultiSelect(discord.ui.Select):
    def __init__(self, engines, current_statuses):
        options = []
        for eid, (name, emoji) in engines.items():
            options.append(discord.SelectOption(
                label=name,
                value=eid,
                emoji=emoji,
                default=current_statuses.get(eid, False)
            ))
        
        super().__init__(
            placeholder="Select engines to ENABLE (deselected = DISABLED)",
            min_values=0,
            max_values=len(engines),
            options=options
        )
        self.engines = engines

    async def callback(self, interaction: discord.Interaction):
        # Respond immediately to avoid timeout
        await interaction.response.defer()
        
        selected_ids = self.values
        all_ids = list(self.engines.keys())
        
        changes_made = []
        for eid in all_ids:
            is_enabled = eid in selected_ids
            current = await unified_cache.is_engine_enabled(eid)
            if is_enabled != current:
                await unified_cache.set_engine_status(eid, is_enabled)
                status_text = "enabled" if is_enabled else "disabled"
                changes_made.append(f"{self.engines[eid][1]} **{self.engines[eid][0]}** is now {status_text}")

        if not changes_made:
            return await interaction.followup.send("No changes were made.", ephemeral=True)

        # Update the original message
        new_desc = ""
        for eid, (name, emoji) in self.engines.items():
            enabled = eid in selected_ids
            dot = "🟢" if enabled else "🔴"
            new_desc += f"{emoji} **{name}**: {dot}\n\n"
        
        # Edit the main panel using the view's update method
        try:
            await self.view.update_panel(interaction, new_desc, selected_ids)
        except Exception as e:
            print(f"Error editing message: {e}")

        await interaction.followup.send(view=owner_design.engine_updated(changes_made), ephemeral=True)

class EngineControlView(discord.ui.LayoutView):
    def __init__(self, engines, current_statuses, author_id):
        # LayoutView might not take timeout in __init__
        super().__init__()
        self.timeout = 60
        self.engines = engines
        self.author_id = author_id
        self.message = None
        
        # Build initial status description
        desc = ""
        for eid, (name, emoji) in engines.items():
            enabled = current_statuses.get(eid, False)
            dot = "🟢" if enabled else "🔴"
            desc += f"{emoji} **{name}**: {dot}\n\n"

        self.status_display = discord.ui.TextDisplay(content=f"## Engine Control Panel\n{desc}")
        self.separator = discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
        self.status_container = discord.ui.Container(self.status_display, self.separator, accent_color=EMBED_COLOR)
        
        self.select_menu = EngineMultiSelect(engines, current_statuses)
        self.select_row = discord.ui.ActionRow()
        self.select_row.add_item(self.select_menu)
        
        # Add items to LayoutView
        self.add_item(self.status_container)
        self.add_item(self.select_row)

    async def update_panel(self, interaction: discord.Interaction, new_desc: str, selected_ids: list):
        # Update current selected defaults for next interaction
        for option in self.select_menu.options:
            option.default = option.value in selected_ids

        # Update the existing display content instead of rebuilding everything
        self.status_display.content = f"## Engine Control Panel\n{new_desc}"
        
        # Use edit_original_response because the interaction was deferred
        await interaction.edit_original_response(view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        # Remove the select menu after timeout
        if self.message:
            try:
                await self.message.edit(view=None)
            except Exception:
                # Silently catch errors if message was deleted
                pass

class EngineControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="engine-control", aliases=["ec"])
    async def engine_control(self, ctx):
        """Manage engine status globally via a multi-select menu."""
        # Defer to prevent "Application did not respond"
        await ctx.defer()

        if not is_bot_owner(ctx.author.id):
            await ctx.send(view=owner_design.permission_denied(), ephemeral=True)
            return

        engines = {
            "ytmsearch": ("YouTube Music", YTMUSIC),
            "dzsearch": ("Deezer", DEEZER),
            "spsearch": ("Spotify", SPOTIFY),
            "jssearch": ("JioSaavn", JIOSAAVN),
            "scsearch": ("SoundCloud", SOUNDCLOUD),
            "ytsearch": ("YouTube", YOUTUBE),
            "amsearch": ("Apple Music", APPLE_MUSIC),
            "ytdl": ("yt-dlp", YTDLP)
        }

        current_statuses = {}
        for eid, (name, emoji) in engines.items():
            enabled = await unified_cache.is_engine_enabled(eid)
            current_statuses[eid] = enabled

        view = EngineControlView(engines, current_statuses, ctx.author.id)
        
        # ctx.send for hybrid command returns the message
        msg = await ctx.send(view=view)
        # Store message for timeout handling
        view.message = msg

async def setup(bot):
    await bot.add_cog(EngineControl(bot))
