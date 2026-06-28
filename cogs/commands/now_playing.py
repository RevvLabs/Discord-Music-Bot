import os
import random
import asyncio
import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from utils.helper_function.setup_enforcer import enforce_setup
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from dotenv import load_dotenv

from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import now_playing as np_design
from utils.helper_function.auto_delete import schedule_delete
from utils.helper_function.safe_send import safe_send_file

load_dotenv()
BOT_NAME = os.getenv("BOT_NAME", "Mewzik")

FONT_PATH  = "fonts/PetrovSans-SemiBold.ttf"
FONT_PATH3 = "fonts/Mocosans-SimpleNote.ttf"

GRADIENTS = [
    ((0,   49,  97),  (0,  106, 103)),
    ((33,  53,  85),  (62,  88, 121)),
    ((75,  89,  69),  (102, 120,  95)),
    ((27,  24,  51),  (68,  23,  82)),
    ((70,  20,  20),  (40,  20,  60)),
    ((20,  40,  80),  (10,  70,  50)),
    ((40,  20,  60),  (10,  50,  80)),
]


def _fit_text(text: str, font, draw, max_px: int) -> str:
    """Truncate text with ellipsis to fit within max_px width."""
    if draw.textbbox((0, 0), text, font=font)[2] <= max_px:
        return text
    while len(text) > 1:
        text = text[:-1]
        if draw.textbbox((0, 0), text + "…", font=font)[2] <= max_px:
            return text + "…"
    return text


class Now_Playing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_time(self, milliseconds: int) -> str:
        s = milliseconds // 1000
        return f"{s // 60}:{s % 60:02d}"

    def _render_now_playing_image(
        self,
        artwork_bytes: bytes | None,
        song_title: str,
        song_author: str,
        requested_by,
        progress_percent: float,
        position: int,
        length: int,
    ) -> BytesIO:
        # Pure-CPU PIL rendering — must be called via asyncio.to_thread so it
        # never blocks the event loop.
        W, H = 1000, 330
        PAD = 20

        # ── Background gradient ───────────────────────────────────────────────
        gs, ge = random.choice(GRADIENTS)
        base = Image.new("RGB", (W, H), gs)
        bd = ImageDraw.Draw(base)
        for y in range(H):
            r = gs[0] + (ge[0] - gs[0]) * y // H
            g = gs[1] + (ge[1] - gs[1]) * y // H
            b = gs[2] + (ge[2] - gs[2]) * y // H
            bd.line([(0, y), (W, y)], fill=(r, g, b))
        img = base.filter(ImageFilter.GaussianBlur(45)).convert("RGBA")

        # Dark left panel behind artwork
        left_panel = Image.new("RGBA", (310, H), (0, 0, 0, 70))
        img.alpha_composite(left_panel, (0, 0))

        draw = ImageDraw.Draw(img)

        # ── Fonts ─────────────────────────────────────────────────────────────
        f_header  = ImageFont.truetype(FONT_PATH, 17)
        f_title   = ImageFont.truetype(FONT_PATH, 36)
        f_artist  = ImageFont.truetype(FONT_PATH, 22)
        f_meta    = ImageFont.truetype(FONT_PATH, 16)
        f_time    = ImageFont.truetype(FONT_PATH, 15)
        f_wm      = ImageFont.truetype(FONT_PATH3, 22)

        WHITE  = (255, 255, 255, 255)
        DIM    = (200, 200, 210, 255)
        FAINT  = (150, 150, 165, 255)
        GREEN  = (100, 220, 140, 230)

        # ── Artwork ───────────────────────────────────────────────────────────
        AW = 270
        AH = 270
        AX = (310 - AW) // 2       # centered in left panel
        AY = (H - AH) // 2

        try:
            if not artwork_bytes:
                raise ValueError("no artwork")
            art = Image.open(BytesIO(artwork_bytes)).resize((AW, AH)).convert("RGBA")

            radius = 18
            mask = Image.new("L", (AW, AH), 0)
            ImageDraw.Draw(mask).rounded_rectangle([(0, 0), (AW, AH)], radius=radius, fill=255)
            art.putalpha(mask)

            # White border
            BW, BH = AW + 8, AH + 8
            border = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
            ImageDraw.Draw(border).rounded_rectangle(
                [(0, 0), (BW - 1, BH - 1)], radius=radius + 3, fill=(255, 255, 255, 180)
            )
            img.alpha_composite(border, (AX - 4, AY - 4))
            img.alpha_composite(art, (AX, AY))
        except Exception:
            draw.rounded_rectangle([AX, AY, AX + AW, AY + AH], radius=18, fill=(70, 70, 85))
            draw = ImageDraw.Draw(img)

        # ── Vertical separator ────────────────────────────────────────────────
        sep_x = 315
        img.alpha_composite(Image.new("RGBA", (2, H - 30), (255, 255, 255, 55)), (sep_x, 15))

        # ── Right area ────────────────────────────────────────────────────────
        RX = sep_x + 22
        RW = W - RX - PAD
        draw = ImageDraw.Draw(img)

        # Header label
        draw.text((RX, PAD + 2), "NOW PLAYING", font=f_header, fill=FAINT)

        # Watermark — top right
        wm_bbox = draw.textbbox((0, 0), BOT_NAME, font=f_wm)
        wm_w = wm_bbox[2] - wm_bbox[0]
        wm_ol = Image.new("RGBA", (wm_w + 4, 28), (0, 0, 0, 0))
        ImageDraw.Draw(wm_ol).text((2, 2), BOT_NAME, font=f_wm, fill=(255, 255, 255, 100))
        img.alpha_composite(wm_ol, (W - wm_w - PAD - 4, PAD))

        # Divider 1
        div1_y = PAD + 28
        img.alpha_composite(Image.new("RGBA", (RW, 1), (255, 255, 255, 65)), (RX, div1_y))
        draw = ImageDraw.Draw(img)

        # Song title
        title_y = div1_y + 16
        title_text = _fit_text(song_title, f_title, draw, RW)
        draw.text((RX, title_y), title_text, font=f_title, fill=WHITE)

        # Artist
        artist_y = title_y + 48
        artist_text = _fit_text(f"  {song_author}", f_artist, draw, RW)
        draw.text((RX, artist_y), artist_text, font=f_artist, fill=DIM)

        # Requested by
        req_name = getattr(requested_by, "display_name", str(requested_by))
        req_y = artist_y + 32
        req_text = _fit_text(f"Requested by  {req_name}", f_meta, draw, RW)
        draw.text((RX, req_y), req_text, font=f_meta, fill=FAINT)

        # Divider 2
        div2_y = req_y + 26
        img.alpha_composite(Image.new("RGBA", (RW, 1), (255, 255, 255, 65)), (RX, div2_y))
        draw = ImageDraw.Draw(img)

        # Timestamps
        pos_text = self.format_time(position)
        len_text = self.format_time(length)
        time_y = div2_y + 10

        draw.text((RX, time_y), pos_text, font=f_time, fill=FAINT)
        len_bbox = draw.textbbox((0, 0), len_text, font=f_time)
        draw.text((RX + RW - (len_bbox[2] - len_bbox[0]), time_y), len_text, font=f_time, fill=FAINT)

        # Progress bar
        bar_y = time_y + 22
        bar_h = 10

        bar_bg = Image.new("RGBA", (RW, bar_h), (0, 0, 0, 0))
        bar_d = ImageDraw.Draw(bar_bg)
        bar_d.rounded_rectangle([(0, 0), (RW, bar_h)], radius=5, fill=(255, 255, 255, 40))
        filled_w = max(int(RW * (progress_percent / 100)), 10)
        bar_d.rounded_rectangle([(0, 0), (filled_w, bar_h)], radius=5, fill=GREEN)

        # Playhead dot at fill edge
        dot_r = 6
        dot_cx = filled_w
        dot_cy = bar_h // 2
        bar_d.ellipse(
            [dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
            fill=(255, 255, 255, 230)
        )

        img.alpha_composite(bar_bg, (RX, bar_y))

        # ── Save ──────────────────────────────────────────────────────────────
        buf = BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        return buf

    async def generate_now_playing_image(self, artwork_url, song_title, song_author,
                                          requested_by, progress_percent, position, length) -> BytesIO:
        artwork_bytes = None
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
                async with session.get(artwork_url) as resp:
                    if resp.status == 200:
                        artwork_bytes = await resp.read()
        except Exception:
            pass

        return await asyncio.to_thread(
            self._render_now_playing_image,
            artwork_bytes, song_title, song_author,
            requested_by, progress_percent, position, length,
        )

    @commands.hybrid_command(
        name="nowplaying", aliases=["np", "info"],
        description="Displays the current song playing."
    )
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def now_playing(self, ctx):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return

        player: LavaMusic = ctx.guild.voice_client

        if player and player.current:
            track    = player.current
            artwork  = track.artwork or "https://files.shapes.inc/5a628ca9.png"
            length   = track.length
            position = player.position
            metadata = player.metadata.get(track, {})
            requestor = metadata.get("requestor", player.client.user)

            progress_percent = (position / length * 100) if length > 0 else 0

            buf = await self.generate_now_playing_image(
                artwork_url=artwork,
                song_title=track.title,
                song_author=track.author,
                requested_by=requestor,
                progress_percent=progress_percent,
                position=position,
                length=length,
            )

            # If the guild has file uploads limited (Discord error 400001),
            # safe_send_file posts the text fallback instead of failing silently.
            fallback = np_design.now_playing_text(
                title=track.title,
                author=track.author,
                requested_by=getattr(requestor, "mention", str(requestor)),
                elapsed=self.format_time(position),
                duration=self.format_time(length),
                progress_percent=progress_percent,
            )
            schedule_delete(await safe_send_file(
                ctx, data=buf, filename="now_playing.png", fallback=fallback,
            ))
        else:
            schedule_delete(await ctx.send(view=np_design.not_playing()))


async def setup(bot):
    await bot.add_cog(Now_Playing(bot))
