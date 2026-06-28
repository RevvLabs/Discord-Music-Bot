import discord
from discord.ext import commands, tasks
import voltricx
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.unified_cache_manager import unified_cache
from utils.helper_function.autoplay_cache import autoplay_cache
from utils.embed_designs.voltricx_events import rejoin_failed
import asyncpg
import asyncio
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

class AutoStop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._rejoin_tasks: dict = {}
        self._rejoin_attempts: dict[int, int] = {}
        self._rejoin_in_progress: set[int] = set()
        self._max_rejoin_attempts = 3
        self.check_vc_task.start()
        
        # Connection pooling and batch processing
        self.pool = None
        self.batch_data = defaultdict(float)  # (guild_id, user_id) -> minutes
        self.batch_lock = asyncio.Lock()
        self.batch_size = 50  # Process in batches of 50
        self.batch_timeout = 5.0  # Process batch after 5 seconds if not full
        self.batch_task = None

    async def cog_load(self):
        """Initialize connection pool when cog loads."""
        DATABASE_URL = os.getenv("DATABASE_URL")
        if DATABASE_URL:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            # Start batch processing task
            self.batch_task = asyncio.create_task(self._batch_processor())

    async def _batch_processor(self):
        """Background task to process batches periodically."""
        while True:
            try:
                await asyncio.sleep(self.batch_timeout)
                await self._process_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in batch processor: {e}")

    async def _process_batch(self):
        """Process the current batch of user_counts updates."""
        if not self.pool:
            return
            
        async with self.batch_lock:
            if not self.batch_data:
                return
                
            # Copy and clear batch data
            batch_items = list(self.batch_data.items())
            self.batch_data.clear()
        
        if not batch_items:
            return
            
        try:
            async with self.pool.acquire() as conn:
                # Use a single transaction for the entire batch
                async with conn.transaction():
                    for (guild_id, user_id), minutes in batch_items:
                        await conn.execute(
                            """
                            INSERT INTO user_counts (guild_id, user_id, minutes)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (guild_id, user_id)
                            DO UPDATE SET minutes = user_counts.minutes + $3
                            """,
                            guild_id, user_id, minutes
                        )
                        
            print(f"Processed batch of {len(batch_items)} user_counts updates")
            
        except Exception as e:
            print(f"Error processing user_counts batch: {e}")
            # Re-add failed items to batch for retry
            async with self.batch_lock:
                for (guild_id, user_id), minutes in batch_items:
                    self.batch_data[(guild_id, user_id)] += minutes

    async def update_user_time(self, guild_id, user_id, minutes):
        """Add user time to batch for efficient processing."""
        if not self.pool:
            # Fallback to direct connection if pool not available
            DATABASE_URL = os.getenv("DATABASE_URL")
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                await conn.execute(
                    """
                    INSERT INTO user_counts (guild_id, user_id, minutes)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id, user_id)
                    DO UPDATE SET minutes = user_counts.minutes + $3
                    """,
                    guild_id, user_id, minutes
                )
            finally:
                await conn.close()
            return
            
        # Add to batch
        async with self.batch_lock:
            self.batch_data[(guild_id, user_id)] += minutes
            
            # If batch is getting large, process it
            if len(self.batch_data) >= self.batch_size:
                await self._process_batch()

    @tasks.loop(seconds=30)
    async def check_vc_task(self):
        if not voltricx.Pool.nodes():
            return  

        for node in voltricx.Pool.nodes().values():
            for player in node.players.values():
                if isinstance(player, LavaMusic):  
                    if player._connected:
                        vc = player.channel
                        # Count only human members
                        human_members = [m for m in vc.members if not m.bot]
                        if len(human_members) == 0: 
                            if isinstance(player.queue, voltricx.Queue):
                                player.queue.mode = voltricx.QueueMode.normal
                            player.filters.reset() 
                            player.filter_name = "None"
                            player.filter_status = False
                            player.queue.clear()
                            player._autoplay = voltricx.AutoPlayMode.partial
                            autoplay_cache.stop_session(player.guild.id)
                            # Release any temp no-prefix VC ownership we held here.
                            try:
                                await unified_cache.delete_vc_assignment(
                                    player.guild.id, vc.id, self.bot.user.id
                                )
                            except Exception:
                                pass
                            if player.playing:
                                try:
                                    await player.stop() 
                                except voltricx.LavalinkException as e:
                                    print(f"Error stopping player: {e}")
                                    continue
                        
                        elif player.playing:
                            for member in vc.members:
                                if member.bot:
                                    continue
                                user_id = member.id
                                guild_id = member.guild.id
                                await self.update_user_time(guild_id, user_id, 0.5)


    @check_vc_task.before_loop
    async def before_check_vc_task(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.id != self.bot.user.id:
            return
        # Bot connected to a channel — reset rejoin failure counter only if not mid-rejoin
        # (a connect event fires during the rejoin attempt itself; resetting there causes infinite loop)
        if after.channel is not None:
            if member.guild.id not in self._rejoin_in_progress:
                self._rejoin_attempts.pop(member.guild.id, None)
            return
        # Bot disconnected (had a channel, now has none)
        if before.channel is None:
            return

        guild = member.guild

        # Release any temp no-prefix VC ownership for the channel we just left.
        try:
            await unified_cache.delete_vc_assignment(guild.id, before.channel.id, self.bot.user.id)
        except Exception:
            pass

        attempts = self._rejoin_attempts.get(guild.id, 0)
        if attempts >= self._max_rejoin_attempts:
            return

        # Cancel any existing pending rejoin for this guild
        existing = self._rejoin_tasks.pop(guild.id, None)
        if existing:
            existing.cancel()

        self._rejoin_tasks[guild.id] = asyncio.ensure_future(
            self._delayed_rejoin(guild)
        )

    async def _delayed_rejoin(self, guild: discord.Guild):
        await asyncio.sleep(5)
        self._rejoin_tasks.pop(guild.id, None)

        # Already reconnected
        if guild.voice_client is not None:
            return

        bot_id = self.bot.user.id if self.bot.user else 0
        channel_data = await unified_cache.get_channel_set_data(guild.id, bot_id)
        if not channel_data:
            return

        voice_channel = guild.get_channel(channel_data["voice_channel_id"])
        if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
            return

        self._rejoin_attempts[guild.id] = self._rejoin_attempts.get(guild.id, 0) + 1
        self._rejoin_in_progress.add(guild.id)
        try:
            existing_vc = guild.voice_client
            if existing_vc:
                try:
                    await existing_vc.disconnect(force=True)
                except Exception:
                    pass

            # Reset Discord gateway voice state so it issues fresh voice server credentials
            # instead of reusing the same broken server from the stale session
            try:
                await guild.change_voice_state(channel=None)
            except Exception:
                pass
            await asyncio.sleep(2)

            await voice_channel.connect(cls=LavaMusic)
            self._rejoin_in_progress.discard(guild.id)
            self._rejoin_attempts.pop(guild.id, None)
            try:
                await voice_channel.edit(status="Ready to Play !")
            except discord.Forbidden:
                pass
            print(f"\033[92m[INFO] Auto-rejoined\033[0m: {voice_channel.name} in {guild.name}")
        except Exception as e:
            self._rejoin_in_progress.discard(guild.id)
            attempts = self._rejoin_attempts.get(guild.id, 0)
            remaining = self._max_rejoin_attempts - attempts
            print(f"\033[91m[ERROR] Auto-rejoin failed\033[0m: {guild.name} — {e}{' (giving up)' if remaining <= 0 else f' ({remaining} attempts left)'}")
            if remaining <= 0:
                await self._cleanup_after_failed_rejoin(guild, channel_data)

    async def _cleanup_after_failed_rejoin(self, guild: discord.Guild, channel_data: dict):
        self._rejoin_attempts.pop(guild.id, None)

        # Destroy zombie Lavalink player
        for node in voltricx.Pool.nodes().values():
            player: LavaMusic = node.players.get(guild.id)
            if player:
                autoplay_cache.stop_session(guild.id)
                try:
                    await player.disconnect()
                except Exception:
                    pass
                break

        # Notify setup text channel
        text_channel = guild.get_channel(channel_data.get("text_channel_id"))
        if text_channel and isinstance(text_channel, discord.TextChannel):
            try:
                await text_channel.send(view=rejoin_failed())
            except (discord.Forbidden, discord.HTTPException):
                pass

    def cog_unload(self):
        self.check_vc_task.cancel()
        for task in self._rejoin_tasks.values():
            task.cancel()
        self._rejoin_tasks.clear()
        self._rejoin_attempts.clear()
        self._rejoin_in_progress.clear()

        # Cancel batch processing task
        if self.batch_task:
            self.batch_task.cancel()

        # Process any remaining batch items before unloading
        if self.pool:
            asyncio.create_task(self._process_batch())
            asyncio.create_task(self.pool.close())

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoStop(bot))