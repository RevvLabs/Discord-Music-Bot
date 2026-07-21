import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from utils.helper_function.unified_cache_manager import unified_cache
from utils.embed_designs import mention as mention_design

load_dotenv()
BOT_NAME = os.getenv("BOT_NAME")

class Mention(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_prefix(self, guild_id):
        bot_id = self.bot.user.id if self.bot.user else 0
        return await unified_cache.get_prefix(guild_id, bot_id)

    async def get_channels_from_db(self, guild_id):
        bot_id = self.bot.user.id if self.bot.user else 0
        data = await unified_cache.get_channel_set_data(guild_id, bot_id)
        if data:
            return (data["player_channel_id"], data["voice_channel_id"])
        return None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        is_blacklisted = await unified_cache.is_user_blacklisted(message.author.id)
        if is_blacklisted:
            return

        if self.bot.user in message.mentions and len(message.content.split()) == 1 and message.reference is None:
            try:
                prefix = await self.get_prefix(message.guild.id)
            except Exception:
                prefix = os.getenv("PREFIX", "-")

            setup_info = ""
            bot_id = self.bot.user.id if self.bot.user else 0
            try:
                setup_result = await self.get_channels_from_db(message.guild.id)
                if setup_result:
                    player_channel_id, voice_channel_id = setup_result
                    player_channel = self.bot.get_channel(player_channel_id)
                    voice_channel = self.bot.get_channel(voice_channel_id)
                    if player_channel and voice_channel:
                        setup_info = (
                            f"Text Channel is set to  : {player_channel.mention}\n"
                            f"Voice Channel is set to : {voice_channel.mention}\n\n"
                        )
                else:
                    # No permanent setup — surface any active temp VC ownership
                    # (no-prefix mode) so the user can see where the bot is bound.
                    temp = await unified_cache.get_bot_vc_assignments(message.guild.id, bot_id)
                    lines = []
                    for a in temp:
                        vc = self.bot.get_channel(a["voice_channel_id"])
                        tc = self.bot.get_channel(a["text_channel_id"]) if a["text_channel_id"] else None
                        if vc:
                            line = f"Temp Voice Channel : {vc.mention}"
                            if tc:
                                line += f"  ·  Text : {tc.mention}"
                            lines.append(line)
                    if lines:
                        setup_info = "🔗 **Temporary setup active**\n" + "\n".join(lines) + "\n\n"
            except Exception:
                pass

            # DJ role (independent of channel setup — show whenever configured)
            try:
                dj_role_id = await unified_cache.get_dj_role(message.guild.id)
                if dj_role_id and message.guild.get_role(dj_role_id):
                    setup_info += f"DJ Role is set to : <@&{dj_role_id}>\n\n"
            except Exception:
                pass

            try:
                view = mention_design.greeting(BOT_NAME, prefix, setup_info)
                support_url = os.getenv("SUPPORT_SERVER_URL")
                if support_url:
                    row = discord.ui.ActionRow()
                    row.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=support_url))
                    view.add_item(row)
                await message.reply(view=view)
            except Exception as e:
                print(f"\033[91m[ERROR] Mention reply failed\033[0m: {e}")

async def setup(bot):
    await bot.add_cog(Mention(bot))
