import discord
import os
from dotenv import load_dotenv

load_dotenv()

_color_str = os.getenv("EMBED_COLOR", "2b2d31")
EMBED_COLOR = discord.Color(int(_color_str, 16))

# Bot display name — used in user-facing embeds/footers. Falls back to "Mewzik".
BOT_NAME = os.getenv("BOT_NAME", "Mewzik")
