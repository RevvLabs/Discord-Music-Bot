import discord
from utils.helper_function.bot_config import EMBED_COLOR
from emojis import PREV_BTN, NEXT_BTN, OPTIONS_BTN

class PaginationView(discord.ui.LayoutView):
    def __init__(self, chunks, create_embed_fn, ctx=None, interaction=None, criteria_callback=None, current_page=0):
        super().__init__(timeout=60)
        self.chunks = chunks
        self.create_embed_fn = create_embed_fn
        self.current_page = current_page
        self.message: discord.Message | None = None

        self.ctx_author = interaction.user if interaction else ctx.author
        self.criteria_callback = criteria_callback
        
        # Create persistent components
        self.header = discord.ui.TextDisplay(content="### Results")
        self.display = discord.ui.TextDisplay(content="")
        self.footer = discord.ui.TextDisplay(content="")

        # Create the action row for buttons
        self.row = discord.ui.ActionRow()

        self.prev_button = discord.ui.Button(label="Previous", emoji=PREV_BTN, style=discord.ButtonStyle.secondary)
        self.next_button = discord.ui.Button(label="Next", emoji=NEXT_BTN, style=discord.ButtonStyle.secondary)

        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page

        # Add items via the action row or directly to the LayoutView
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = self.current_page <= 0
        self.next_button.disabled = self.current_page >= len(self.chunks) - 1

        self.clear_items()
        self.row.clear_items()
        
        # Update content
        result = self.create_embed_fn(self)
        
        container_items = []
        if isinstance(result, list):
            container_items = result
        elif isinstance(result, discord.Embed):
            # Legacy/Fallback: Convert Embed to Container items
            if result.title:
                container_items.append(discord.ui.TextDisplay(content=f"## {result.title}"))
            if result.description:
                container_items.append(discord.ui.TextDisplay(content=result.description))
            if result.footer:
                container_items.append(discord.ui.TextDisplay(content=f"---\n{result.footer.text}"))
        else:
            container_items = [discord.ui.TextDisplay(content=str(result))]
            
        container = discord.ui.Container(*container_items, accent_color=EMBED_COLOR)
        self.add_item(container)

        self.row.add_item(self.prev_button)
        self.row.add_item(self.next_button)

        if self.criteria_callback:
            criteria_button = discord.ui.Button(label="Change Criteria", emoji=OPTIONS_BTN, style=discord.ButtonStyle.primary)
            criteria_button.callback = self.criteria_callback
            self.row.add_item(criteria_button)
        
        self.add_item(self.row)

    async def prev_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx_author:
            await interaction.response.send_message("You cannot control this pagination.", ephemeral=True)
            return

        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx_author:
            await interaction.response.send_message("You cannot control this pagination.", ephemeral=True)
            return

        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(view=self)

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

    def create_embed(self):
        return self.create_embed_fn(self)