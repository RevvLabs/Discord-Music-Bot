import discord
from discord.ext import commands
from discord.ui import Button
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.dj_checker import dj_lockable
from emojis import JIOSAAVN, SPOTIFY, YTMUSIC, SOUNDCLOUD, YOUTUBE, DEEZER, APPLE_MUSIC, YTDLP
from utils.embed_designs import engine as engine_design

load_dotenv()


class EngineSelector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="engine", description="Choose your search engine.", aliases=['eng'])
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    @dj_lockable()
    async def select_engine(self, ctx: commands.Context):
        await ctx.defer()

        engines = {
            "ytsearch":  ("YouTube",       YOUTUBE),
            "dzsearch":  ("Deezer",         DEEZER),
            "ytmsearch": ("YouTube Music",  YTMUSIC),
            "spsearch":  ("Spotify",        SPOTIFY),
            "jssearch":  ("JioSaavn",       JIOSAAVN),
            "scsearch":  ("SoundCloud",     SOUNDCLOUD),
            "amsearch":  ("Apple Music",    APPLE_MUSIC),
            "ytdl":      ("yt-dlp",         YTDLP),
        }

        from utils.helper_function.unified_cache_manager import unified_cache

        layout_view = engine_design.engine_picker()

        enabled_buttons = []

        auto_button = Button(label="Auto 🎶", style=discord.ButtonStyle.primary, custom_id="engine_auto")

        async def auto_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message(view=engine_design.not_authorized(), ephemeral=True)
                return
            try:
                await unified_cache.set_user_engine(interaction.user.id, None)
                await interaction.response.edit_message(view=engine_design.engine_reset())
            except Exception as e:
                await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

        auto_button.callback = auto_callback
        enabled_buttons.append(auto_button)

        for engine_id, (engine_name, engine_emoji) in engines.items():
            if not await unified_cache.is_engine_enabled(engine_id):
                continue

            button = Button(
                label=engine_name,
                style=discord.ButtonStyle.secondary,
                emoji=engine_emoji,
                custom_id=f"engine_{engine_id}",
            )

            async def button_callback(interaction: discord.Interaction, eid=engine_id):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message(view=engine_design.not_authorized(), ephemeral=True)
                    return
                try:
                    await unified_cache.set_user_engine(interaction.user.id, eid)
                    emoji, name = engines[eid][1], engines[eid][0]
                    await interaction.response.edit_message(view=engine_design.engine_selected(emoji, name))
                except Exception as e:
                    await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

            button.callback = button_callback
            enabled_buttons.append(button)

        for i in range(0, len(enabled_buttons), 5):
            row = discord.ui.ActionRow()
            for button in enabled_buttons[i:i + 5]:
                row.add_item(button)
            layout_view.add_item(row)

        layout_view.timeout = 60
        msg = await ctx.send(view=layout_view)

        async def _on_engine_timeout():
            try:
                await msg.delete()
            except Exception:
                pass

        layout_view.on_timeout = _on_engine_timeout


async def setup(bot):
    await bot.add_cog(EngineSelector(bot))
