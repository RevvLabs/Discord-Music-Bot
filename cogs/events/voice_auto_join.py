from discord.ext import commands
import discord
import asyncio
import os
from dotenv import load_dotenv
from utils.helper_function.VoltricxPlayer import LavaMusic
from utils.helper_function.unified_cache_manager import unified_cache
from utils.helper_function.session_manager import session_manager
from utils.embed_designs import session as session_design

load_dotenv()

class VoiceAutoJoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_setup_voice_channel(self, guild: discord.Guild):
        bot_id = self.bot.user.id if self.bot.user else 0
        channel_data = await unified_cache.get_channel_set_data(guild.id, bot_id)
        if not channel_data:
            return None
        return guild.get_channel(channel_data["voice_channel_id"])

    async def _connect(self, channel: discord.VoiceChannel):
        perms = channel.permissions_for(channel.guild.me)
        if not perms.connect or not perms.speak:
            return
        try:
            await channel.connect(cls=LavaMusic, timeout=30, reconnect=True, self_deaf=True)
            try:
                await channel.edit(status="Ready to Play !")
            except discord.Forbidden:
                pass
            print(f"\033[92m[INFO] Auto-joined\033[0m: {channel.name} in {channel.guild.name}")
        except Exception as e:
            print(f"\033[91m[ERROR] Auto-join failed\033[0m: {channel.guild.name} — {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(5)
        for guild in self.bot.guilds:
            if guild.voice_client is not None:
                continue
            channel = await self._get_setup_voice_channel(guild)
            if channel and isinstance(channel, discord.VoiceChannel):
                await self._connect(channel)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        is_blacklisted = await unified_cache.is_user_blacklisted(member.id)
        if is_blacklisted:
            return

        guild = member.guild

        # Auto-unlock session if the session owner leaves the voice channel
        if before.channel is not None and (after.channel is None or after.channel != before.channel):
            info = session_manager.get_info(guild.id)
            if info and info.owner_id == member.id:
                session_manager.unlock(guild.id)

                # Resolve the notification channel: prefer vc.home, fall back to setup player channel
                notify_channel = None
                vc: LavaMusic | None = guild.voice_client
                notify_channel = getattr(vc, "home", None) if vc else None

                if notify_channel is None:
                    bot_id = self.bot.user.id if self.bot.user else 0
                    channel_data = await unified_cache.get_channel_set_data(guild.id, bot_id)
                    if channel_data:
                        notify_channel = guild.get_channel(channel_data["player_channel_id"])

                if notify_channel:
                    try:
                        from utils.helper_function.auto_delete import schedule_delete
                        schedule_delete(
                            await notify_channel.send(
                                view=session_design.session_auto_unlocked(info.owner_name)
                            )
                        )
                    except Exception:
                        pass

        # User joined a voice channel — auto-connect if configured
        if before.channel is None and after.channel is not None:
            if guild.voice_client is not None:
                return

            channel = await self._get_setup_voice_channel(guild)
            if channel and after.channel.id == channel.id:
                await self._connect(channel)


async def setup(bot):
    await bot.add_cog(VoiceAutoJoin(bot))
