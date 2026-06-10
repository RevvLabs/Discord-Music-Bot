import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import voltricx
from voltricx.player import Player
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import owner as owner_design

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
            await interaction.response.send_message("Confirmed. Proceeding with force fix...", ephemeral=True)
        else:
            await interaction.response.send_message("You must type 'confirm' to proceed.", ephemeral=True)

class ForceFixCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="forcefix", description="Force fixes all voice connections.", aliases=["ff"])
    async def forcefix(self, ctx: commands.Context):
        if ctx.author.id not in BOT_OWNER_IDS:
            return await ctx.send(view=owner_design.permission_denied())

        if ctx.interaction is not None:
            modal = ConfirmModal()
            await ctx.interaction.response.send_modal(modal)
            try:
                await modal.wait()
            except Exception:
                pass

            if not modal.confirmed:
                await ctx.send(view=owner_design.no_confirmation())
                return
        else:
            class ForceFixView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=30)
                    self.confirmed = False

                @discord.ui.button(label="Confirm Force Fix", style=discord.ButtonStyle.danger, emoji="⚠️")
                async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    modal = ConfirmModal()
                    await interaction.response.send_modal(modal)
                    try:
                        await modal.wait()
                        if modal.confirmed:
                            self.confirmed = True
                            self.stop()
                    except Exception:
                        pass

                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
                async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.send_message("Command cancelled.", ephemeral=True)
                    self.stop()

            view = ForceFixView()
            layout_view = owner_design.force_fix_warning()
            layout_view.add_item(view)
            await ctx.send(view=layout_view)

            try:
                await view.wait()
            except Exception:
                pass

            if not view.confirmed:
                await ctx.send(view=owner_design.no_confirmation())
                return

        try:
            player: Player = ctx.guild.voice_client

            if player:
                await player.disconnect()

            for vc in self.bot.voice_clients:
                await vc.disconnect(force=True)

            await ctx.send(view=owner_design.force_fix_success())

        except Exception as e:
            print(e)
            await ctx.send(view=owner_design.force_fix_error())

async def setup(bot):
    await bot.add_cog(ForceFixCog(bot))
