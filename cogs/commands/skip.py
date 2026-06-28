import asyncio
import discord
import discord.utils
from discord.ext import commands
from discord.ext.commands import BucketType
from dotenv import load_dotenv

from utils.check_decorators.blacklist_checker import is_not_blacklisted
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.voice_connected import ensure_voice
from utils.helper_function.setup_enforcer import enforce_setup
from utils.helper_function.unified_cache_manager import unified_cache
from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import skip as skip_design
from utils.helper_function.auto_delete import schedule_delete

load_dotenv()


class Skip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _is_dj(self, ctx: commands.Context) -> bool:
        """True if the author holds the guild's configured DJ role."""
        dj_role_id = await unified_cache.get_dj_role(ctx.guild.id)
        if not dj_role_id:
            return False
        return any(r.id == dj_role_id for r in getattr(ctx.author, "roles", []))

    async def start_vote_skip(self, ctx: commands.Context, player: LavaMusic):
        try:
            if not await enforce_setup(ctx, EMBED_COLOR):
                return

            # DJ role bypass — skip instantly, no vote, regardless of VC size.
            if await self._is_dj(ctx):
                try:
                    await player.skip()
                    if player.paused:
                        await player.pause(False)
                    await ctx.send(view=skip_design.skipped(), ephemeral=True)
                    return False
                except Exception as e:
                    print(f"\033[91m[ERROR] DJ Skip Error\033[0m: {e}")
                    return False

            channel = ctx.author.voice.channel
            members_in_vc = len([m for m in channel.members if not m.bot])

            if members_in_vc <= 3:
                try:
                    await player.skip()
                    if player.paused:
                        await player.pause(False)
                    await ctx.send(view=skip_design.skipped(), ephemeral=True)
                    return False
                except Exception as e:
                    print(f"\033[91m[ERROR] Skip Player Error\033[0m: {e}")
                    return False

            timestamp = int(discord.utils.utcnow().timestamp())
            vote_message = await ctx.send(view=skip_design.vote_started(timestamp))
            await vote_message.add_reaction("✅")
            await vote_message.add_reaction("❌")
            schedule_delete(vote_message, 90)

            votes = {"✅": 0, "❌": 0}

            def check(reaction, user):
                return not user.bot and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == vote_message.id

            try:
                while True:
                    reactions = await self.bot.wait_for("reaction_add", check=check, timeout=25.0)
                    if reactions:
                        if reactions[0].emoji == "✅":
                            votes["✅"] += 1
                        elif reactions[0].emoji == "❌":
                            votes["❌"] += 1
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"\033[91m[ERROR] Vote Collection Error\033[0m: {e}")

            total_votes = sum(votes.values())
            if total_votes > 0 and (votes["✅"] / total_votes) >= 0.51:
                try:
                    await player.skip()
                    await vote_message.edit(view=skip_design.vote_skipped())
                    schedule_delete(vote_message)
                    return True
                except Exception as e:
                    print(f"\033[91m[ERROR] Vote Skip Execution Error\033[0m: {e}")
                    return False
            else:
                try:
                    await vote_message.edit(view=skip_design.vote_failed())
                    schedule_delete(vote_message)
                    return False
                except Exception as e:
                    print(f"\033[91m[ERROR] Vote Failed Message Error\033[0m: {e}")
                    return False
        except Exception as e:
            print(f"\033[91m[ERROR] Vote Skip General Error\033[0m: {e}")
            return False

    @commands.hybrid_command(name="skip", description="Skip the currently playing track.")
    @commands.cooldown(1, 3, BucketType.user)
    @is_not_blacklisted()
    @maintenance_check()
    async def skip(self, ctx: commands.Context):
        try:
            if not await ensure_voice(ctx):
                return

            player: LavaMusic = ctx.guild.voice_client
            if not player or not player.playing:
                await ctx.send(view=skip_design.not_playing(), ephemeral=True)
                return

            try:
                vote_skipped = await self.start_vote_skip(ctx, player)
                if vote_skipped:
                    return
            except Exception as e:
                print(f"\033[91m[ERROR] Vote Skip Command Error\033[0m: {e}")
                await ctx.send(view=skip_design.skip_error(), ephemeral=True)

        except Exception as e:
            print(f"\033[91m[ERROR] Skip Command Error\033[0m: {e}")
            await ctx.send(view=skip_design.error(str(e)), ephemeral=True)

async def setup(bot) -> None:
    await bot.add_cog(Skip(bot))
