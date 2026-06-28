import os
import random
import asyncio
import aiohttp
import asyncpg
import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dotenv import load_dotenv
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.dj_checker import dj_check_member
from utils.helper_function.auto_delete import schedule_delete
from utils.helper_function.safe_send import safe_send_file

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
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

BADGES = [
    ("Beginner",           1),
    ("Casual Listener",  100),
    ("Playlist Explorer", 200),
    ("Genre Enthusiast",  400),
    ("Album Collector",   800),
    ("Concert Goer",     1200),
    ("Lyric Analyst",    1500),
    ("Music Historian",  2000),
    ("Superfan",         2500),
    ("Audiophile",       3000),
    ("Music Critic",     3600),
    ("Trendsetter",      4200),
    ("Setlist Curator",  5000),
    ("Music Virtuoso",   6000),
    ("Soundtrack To Life", 7000),
    ("Timeless Listener", 10000),
]


def _badge_info(songs):
    current = BADGES[0][0]
    next_name = None
    progress = 0.0
    for name, threshold in BADGES:
        if songs >= threshold:
            current = name
        else:
            next_name = name
            progress = (songs / threshold) * 100
            break
    return current, next_name, progress


def _time_str(minutes: float) -> str:
    m = int(minutes)
    if m >= 60:
        return f"{m // 60}h {m % 60}m"
    return f"{m}m"


def _draw_rounded_bar(draw, x, y, w, h, radius, bg_color, fill_color, fill_pct):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=bg_color)
    filled_w = max(int(w * fill_pct), radius * 2 + 1)
    draw.rounded_rectangle([x, y, x + filled_w, y + h], radius=radius, fill=fill_color)


def _paste_rgba(base: Image.Image, overlay: Image.Image, pos):
    base.paste(overlay, pos, overlay)


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _render_profile_card(
        self,
        avatar_bytes: bytes | None,
        display_name: str,
        total_songs: int,
        total_minutes: float,
        server_rank,
        server_songs: int,
        fav_count: int,
        playlist_count: int,
        source_rows: list,
        guild_name: str,
    ) -> BytesIO:
        # Pure-CPU PIL rendering — must be called via asyncio.to_thread so it
        # never blocks the event loop.
        W, H = 1000, 460
        PAD = 22

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

        # Semi-transparent dark vignette on left panel
        left_panel = Image.new("RGBA", (230, H), (0, 0, 0, 60))
        img.alpha_composite(left_panel, (0, 0))

        draw = ImageDraw.Draw(img)

        # ── Fonts ─────────────────────────────────────────────────────────────
        f_title   = ImageFont.truetype(FONT_PATH, 34)
        f_stat    = ImageFont.truetype(FONT_PATH, 30)
        f_section = ImageFont.truetype(FONT_PATH, 17)
        f_label   = ImageFont.truetype(FONT_PATH, 15)
        f_name    = ImageFont.truetype(FONT_PATH, 22)
        f_badge   = ImageFont.truetype(FONT_PATH, 14)
        f_wm      = ImageFont.truetype(FONT_PATH3, 22)

        WHITE      = (255, 255, 255, 255)
        DIM        = (200, 200, 210, 255)
        FAINT      = (155, 155, 170, 255)
        BAR_BG     = (255, 255, 255, 35)
        BAR_FILL   = (255, 255, 255, 200)
        PROG_FILL  = (100, 220, 140, 230)

        # ── Avatar ────────────────────────────────────────────────────────────
        AV_SIZE = 178
        AV_X, AV_Y = 26, 22
        try:
            if not avatar_bytes:
                raise ValueError("no avatar")
            av = Image.open(BytesIO(avatar_bytes)).resize((AV_SIZE, AV_SIZE)).convert("RGBA")

            # Circular mask
            circ = Image.new("L", (AV_SIZE, AV_SIZE), 0)
            ImageDraw.Draw(circ).ellipse([(0, 0), (AV_SIZE, AV_SIZE)], fill=255)
            av.putalpha(circ)

            # White ring border
            BR = AV_SIZE + 10
            ring = Image.new("RGBA", (BR, BR), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse([(0, 0), (BR - 1, BR - 1)], fill=(255, 255, 255, 210))
            img.alpha_composite(ring, (AV_X - 5, AV_Y - 5))
            img.alpha_composite(av, (AV_X, AV_Y))
        except Exception:
            draw.ellipse([AV_X, AV_Y, AV_X + AV_SIZE, AV_Y + AV_SIZE], fill=(80, 80, 95))

        # Display name (centered in left panel 0–229)
        name_center_x = 115
        bbox = draw.textbbox((0, 0), display_name, font=f_name)
        nw = bbox[2] - bbox[0]
        name_y = AV_Y + AV_SIZE + 12
        draw.text((name_center_x - nw // 2, name_y), display_name, font=f_name, fill=WHITE)

        # Badge label
        current_badge, next_badge, badge_progress = _badge_info(total_songs)
        badge_label = current_badge or "Beginner"
        bbox2 = draw.textbbox((0, 0), badge_label, font=f_badge)
        bw = bbox2[2] - bbox2[0]
        draw.text((name_center_x - bw // 2, name_y + 30), badge_label, font=f_badge, fill=FAINT)

        # ── Vertical separator ────────────────────────────────────────────────
        sep_x = 230
        sep_overlay = Image.new("RGBA", (2, H - 30), (255, 255, 255, 55))
        img.alpha_composite(sep_overlay, (sep_x, 15))

        # ── Right-area constants ──────────────────────────────────────────────
        RX = sep_x + PAD          # right area x start
        RW = W - RX - PAD         # right area usable width

        # ── Title ─────────────────────────────────────────────────────────────
        draw.text((RX, PAD), "MUSIC PROFILE", font=f_title, fill=WHITE)

        # Watermark top-right
        wm_bbox = draw.textbbox((0, 0), BOT_NAME, font=f_wm)
        wm_w = wm_bbox[2] - wm_bbox[0]
        wm_overlay = Image.new("RGBA", (wm_w + 4, 30), (0, 0, 0, 0))
        wm_draw = ImageDraw.Draw(wm_overlay)
        wm_draw.text((2, 2), BOT_NAME, font=f_wm, fill=(255, 255, 255, 110))
        img.alpha_composite(wm_overlay, (W - wm_w - PAD - 4, PAD))

        # Horizontal divider 1
        hdiv1_y = PAD + 46
        hdiv_ol = Image.new("RGBA", (RW, 1), (255, 255, 255, 70))
        img.alpha_composite(hdiv_ol, (RX, hdiv1_y))

        draw = ImageDraw.Draw(img)  # refresh draw after compositing

        # ── Three stat columns ────────────────────────────────────────────────
        col_y = hdiv1_y + 14
        third = RW // 3

        cols = [
            (RX,               "OVERALL",     _time_str(total_minutes), "listening time",
             f"{total_songs:,}", "songs streamed"),
            (RX + third,       "SERVER RANK",  f"#{server_rank}" if server_rank else "N/A", f"in {guild_name[:18]}",
             f"{server_songs:,}", "songs here"),
            (RX + third * 2,   "LIBRARY",      f"{fav_count:,}", "favorites",
             f"{playlist_count:,}", "playlists"),
        ]

        for cx, section_label, val1, sub1, val2, sub2 in cols:
            draw.text((cx, col_y),      section_label, font=f_section, fill=FAINT)
            draw.text((cx, col_y + 24), val1,          font=f_stat,    fill=WHITE)
            draw.text((cx, col_y + 58), sub1,          font=f_label,   fill=DIM)
            draw.text((cx, col_y + 80), val2,          font=f_stat,    fill=WHITE)
            draw.text((cx, col_y + 114), sub2,         font=f_label,   fill=DIM)

        # Horizontal divider 2
        hdiv2_y = col_y + 140
        img.alpha_composite(Image.new("RGBA", (RW, 1), (255, 255, 255, 70)), (RX, hdiv2_y))
        draw = ImageDraw.Draw(img)

        # ── Top sources ───────────────────────────────────────────────────────
        src_y = hdiv2_y + 12
        draw.text((RX, src_y), "TOP SOURCES", font=f_section, fill=FAINT)

        top3 = source_rows[:3]
        total_sc = sum(r["count"] for r in top3) if top3 else 1

        label_col_w = 145
        bar_x = RX + label_col_w
        bar_w = RW - label_col_w - 130
        bar_h = 15
        bar_gap = 34

        for i, row in enumerate(top3):
            sy = src_y + 28 + i * bar_gap
            src_name = row["source"]
            cnt = row["count"]
            pct = cnt / max(total_sc, 1)

            draw.text((RX, sy + 1), src_name, font=f_label, fill=DIM)

            # Bar
            bar_bg_img = Image.new("RGBA", (bar_w, bar_h), (0, 0, 0, 0))
            bar_bg_d = ImageDraw.Draw(bar_bg_img)
            bar_bg_d.rounded_rectangle([(0, 0), (bar_w, bar_h)], radius=6, fill=(255, 255, 255, 35))
            filled_w = max(int(bar_w * pct), 12)
            bar_bg_d.rounded_rectangle([(0, 0), (filled_w, bar_h)], radius=6, fill=(255, 255, 255, 200))
            img.alpha_composite(bar_bg_img, (bar_x, sy))
            draw = ImageDraw.Draw(img)

            # "780 songs" in dim white, then " - " in faint, then "68%" in green
            tx = bar_x + bar_w + 10

            seg1 = f"{cnt:,} songs"
            b1 = draw.textbbox((0, 0), seg1, font=f_label)
            draw.text((tx, sy + 1), seg1, font=f_label, fill=DIM)
            tx += b1[2] - b1[0]

            seg2 = "  -  "
            b2 = draw.textbbox((0, 0), seg2, font=f_label)
            draw.text((tx, sy + 1), seg2, font=f_label, fill=FAINT)
            tx += b2[2] - b2[0]

            draw.text((tx, sy + 1), f"{pct * 100:.0f}%", font=f_label, fill=(120, 220, 150, 230))

        draw = ImageDraw.Draw(img)

        # ── Badge progress bar at bottom ──────────────────────────────────────
        prog_top = H - 58
        img.alpha_composite(Image.new("RGBA", (RW, 1), (255, 255, 255, 70)), (RX, prog_top))
        draw = ImageDraw.Draw(img)

        prog_bar_y = prog_top + 10
        prog_bar_h = 12

        if next_badge:
            bar_bg_prog = Image.new("RGBA", (RW, prog_bar_h), (0, 0, 0, 0))
            bar_bg_d2 = ImageDraw.Draw(bar_bg_prog)
            bar_bg_d2.rounded_rectangle([(0, 0), (RW, prog_bar_h)], radius=5, fill=(255, 255, 255, 40))
            filled_prog = max(int(RW * (badge_progress / 100)), 10)
            bar_bg_d2.rounded_rectangle([(0, 0), (filled_prog, prog_bar_h)], radius=5, fill=(100, 220, 140, 230))
            img.alpha_composite(bar_bg_prog, (RX, prog_bar_y))
            draw = ImageDraw.Draw(img)
            prog_text = f"Next: {next_badge}  ·  {badge_progress:.1f}%"
            draw.text((RX, prog_bar_y + prog_bar_h + 6), prog_text, font=f_label, fill=FAINT)
        else:
            draw.text((RX, prog_bar_y + 4), "✦  Max Level Reached  —  Timeless Listener", font=f_label, fill=FAINT)

        # ── Save ──────────────────────────────────────────────────────────────
        buf = BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        return buf

    async def generate_profile_card(self, user, display_name, total_songs, total_minutes,
                                     server_rank, server_songs, fav_count, playlist_count,
                                     source_rows, guild_name) -> BytesIO:
        avatar_bytes = None
        try:
            url = user.avatar.url if user.avatar else user.default_avatar.url
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        avatar_bytes = await resp.read()
        except Exception:
            pass

        return await asyncio.to_thread(
            self._render_profile_card,
            avatar_bytes, display_name, total_songs, total_minutes,
            server_rank, server_songs, fav_count, playlist_count,
            source_rows, guild_name,
        )

    @commands.hybrid_command(name="profile", description="View your music profile card.")
    @commands.cooldown(1, 5, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def profile(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author

        # Viewing someone else's profile is DJ-only; your own is always allowed.
        if target.id != ctx.author.id:
            allowed, role_id = await dj_check_member(ctx.author, ctx.guild)
            if not allowed:
                from utils.embed_designs import profile as prof_design
                role = ctx.guild.get_role(role_id) if (ctx.guild and role_id) else None
                await ctx.send(
                    view=prof_design.dj_only_others(role.name if role else None),
                    ephemeral=True,
                )
                return

        user_id = target.id
        guild_id = ctx.guild.id

        await ctx.defer()

        conn = None
        try:
            conn = await asyncpg.connect(DATABASE_URL)

            totals = await conn.fetchrow(
                "SELECT COALESCE(SUM(count), 0) AS songs, COALESCE(SUM(minutes), 0) AS minutes "
                "FROM user_counts WHERE user_id = $1",
                user_id
            )
            total_songs   = int(totals["songs"])
            total_minutes = float(totals["minutes"])

            rank_rows = await conn.fetch(
                "SELECT user_id FROM user_counts WHERE guild_id = $1 ORDER BY count DESC, minutes DESC",
                guild_id
            )
            server_rank = next(
                (i + 1 for i, r in enumerate(rank_rows) if r["user_id"] == user_id), None
            )

            server_row = await conn.fetchrow(
                "SELECT count FROM user_counts WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )
            server_songs = int(server_row["count"]) if server_row else 0

            source_rows = await conn.fetch(
                "SELECT source, count FROM user_source_stats WHERE user_id = $1 ORDER BY count DESC",
                user_id
            )

            fav_count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_favorites WHERE user_id = $1", user_id
            ) or 0

            playlist_count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_playlists WHERE user_id = $1", user_id
            ) or 0

        except Exception as e:
            from utils.embed_designs import profile as prof_design
            return schedule_delete(await ctx.send(view=prof_design.db_error(str(e))))
        finally:
            if conn:
                await conn.close()

        buf = await self.generate_profile_card(
            user=target,
            display_name=target.display_name,
            total_songs=total_songs,
            total_minutes=total_minutes,
            server_rank=server_rank,
            server_songs=server_songs,
            fav_count=fav_count,
            playlist_count=playlist_count,
            source_rows=[{"source": r["source"], "count": r["count"]} for r in source_rows],
            guild_name=ctx.guild.name,
        )

        # Upload the card. If the guild has file uploads limited (Discord error
        # 400001), safe_send_file posts the text fallback instead of failing.
        from utils.embed_designs import profile as prof_design
        current_badge, _, _ = _badge_info(total_songs)
        fallback = prof_design.card_text_fallback(
            display_name=target.display_name,
            badge=current_badge or "Beginner",
            total_songs=total_songs,
            listening_time=_time_str(total_minutes),
            server_rank=server_rank,
            server_songs=server_songs,
            fav_count=fav_count,
            playlist_count=playlist_count,
            top_sources=[(r["source"], r["count"]) for r in source_rows[:3]],
            guild_name=ctx.guild.name,
        )
        schedule_delete(await safe_send_file(
            ctx, data=buf, filename="profile_card.png", fallback=fallback,
        ))


async def setup(bot):
    await bot.add_cog(Profile(bot))
