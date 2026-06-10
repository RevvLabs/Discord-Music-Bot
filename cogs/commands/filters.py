import discord
from discord.ext import commands
import voltricx
from voltricx.player import Player
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.helper_function.setup_enforcer import enforce_setup
from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.check_decorators.dj_checker import dynamic_dj_predicate
from utils.helper_function.voice_connected import ensure_voice
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import filters as filters_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Filters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_filters = {}

    async def cog_check(self, ctx: commands.Context) -> bool:
        # Lock every filter command behind the DJ role (raises NotDJ if denied).
        return await dynamic_dj_predicate(ctx)

    async def toggle_filter(self, ctx, filter_type: str):
        if not await enforce_setup(ctx, EMBED_COLOR):
            return
        if not await ensure_voice(ctx):
            return
        player: Player = ctx.guild.voice_client
        if not player:
            schedule_delete(await ctx.send(view=filters_design.not_connected()))
            return

        filters: voltricx.Filters = player.filters

        if filter_type in self.active_filters.get(ctx.guild.id, []):
            filters.reset()
            self.active_filters[ctx.guild.id].remove(filter_type)
            player.filter_name = "None"
            player.filter_status = False
            view = filters_design.filter_disabled(filter_type)
        else:
            if filter_type == "nightcore":
                filters.timescale.set(speed=1.3, pitch=1.2, rate=1)
                player.filter_name = "NightCore"
                player.filter_status = True
            elif filter_type == "vaporwave":
                filters.timescale.set(speed=0.85, pitch=0.8, rate=1)
                filters.rotation.set(rotation_hz=0.2)
                player.filter_name = "VaporWave"
                player.filter_status = True
            elif filter_type == "karaoke":
                filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220, filter_width=100)
                player.filter_name = "Karaoke"
                player.filter_status = True
            elif filter_type == "8d_audio":
                filters.rotation.set(rotation_hz=0.12)
                player.filter_name = "8D"
                player.filter_status = True
            elif filter_type == "chipmunk":
                filters.timescale.set(speed=1.05, pitch=1.8, rate=1)
                player.filter_name = "ChipMunk"
                player.filter_status = True
            elif filter_type == "deep_voice":
                filters.timescale.set(speed=1.0, pitch=0.6, rate=1)
                player.filter_name = "Deep Voice"
                player.filter_status = True
            elif filter_type == "bass_boost":
                filters.equalizer.set(
                    bands=[
                        {"band": 0,  "gain": 0.075},   {"band": 1,  "gain": 0.08375},
                        {"band": 2,  "gain": 0.08375},  {"band": 3,  "gain": 0.05},
                        {"band": 4,  "gain": -0.0625},  {"band": 5,  "gain": 0.01875},
                        {"band": 6,  "gain": -0.05625}, {"band": 7,  "gain": 0.02875},
                        {"band": 8,  "gain": 0.04375},  {"band": 9,  "gain": 0.05625},
                        {"band": 10, "gain": 0.06875},  {"band": 11, "gain": -0.075},
                        {"band": 12, "gain": 0.06875},  {"band": 13, "gain": -0.0625},
                        {"band": 14, "gain": -0.09375},
                    ]
                )
                player.filter_name = "Bass Boost"
                player.filter_status = True
            else:
                schedule_delete(await ctx.send(view=filters_design.invalid_filter(filter_type)))
                return

            await player.set_filters(filters)
            self.active_filters.setdefault(ctx.guild.id, []).append(filter_type)
            view = filters_design.filter_enabled(filter_type)

        await player.set_filters(filters)
        schedule_delete(await ctx.send(view=view))

    @commands.hybrid_command(name="bassboost", description="Toggle the Bass Boost filter.")
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def bass_boost(self, ctx):
        await self.toggle_filter(ctx, "bass_boost")

    @commands.hybrid_command(name="nightcore", description="Toggle the Nightcore filter.")
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    async def nightcore(self, ctx):
        await self.toggle_filter(ctx, "nightcore")

    @commands.hybrid_command(name="vaporwave", description="Toggle the Vaporwave filter.")
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    async def vaporwave(self, ctx):
        await self.toggle_filter(ctx, "vaporwave")

    @commands.hybrid_command(name="karaoke", description="Toggle the Karaoke filter.")
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    async def karaoke(self, ctx):
        await self.toggle_filter(ctx, "karaoke")

    @commands.hybrid_command(name="8d", description="Toggle the 8D Audio filter.")
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    async def eight_d_audio(self, ctx):
        await self.toggle_filter(ctx, "8d_audio")

    @commands.hybrid_command(name="chipmunk", description="Toggle the Chipmunk filter.")
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    async def chipmunk(self, ctx):
        await self.toggle_filter(ctx, "chipmunk")

    @commands.hybrid_command(name="deepvoice", description="Toggle the Deep Voice filter.")
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    async def deep_voice(self, ctx):
        await self.toggle_filter(ctx, "deep_voice")

    @commands.hybrid_command(name="reset", description="Reset all filters.")
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    async def reset_filters(self, ctx):
        player: Player = ctx.guild.voice_client
        if not player:
            schedule_delete(await ctx.send(view=filters_design.not_connected()))
            return

        filters: voltricx.Filters = player.filters
        filters.reset()
        player.filter_name = "None"
        player.filter_status = False
        await player.set_filters(filters)
        self.active_filters[ctx.guild.id] = []
        schedule_delete(await ctx.send(view=filters_design.filters_reset()))

async def setup(bot):
    await bot.add_cog(Filters(bot))
