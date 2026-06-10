import discord
from discord.ext import commands
import voltricx
from utils.helper_function.VoltricxPlayer import LavaMusic

class ResumeHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_cache = {}  

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member == self.bot.user and after.channel is not None and before.channel is None:
            await member.guild.change_voice_state(channel=after.channel, self_mute=False, self_deaf=True)


        if member == self.bot.user and before.channel and not after.channel:
            self.channel_cache[member.guild.id] = before.channel


    @commands.Cog.listener()
    async def on_resumed(self):
        for guild in self.bot.guilds:
            if guild.voice_client:
                player: LavaMusic = guild.voice_client
                if not isinstance(player.queue, voltricx.Queue):
                    player.queue = voltricx.Queue()
            
                

async def setup(bot) -> None:
    await bot.add_cog(ResumeHandler(bot))
