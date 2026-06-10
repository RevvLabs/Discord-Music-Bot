import discord

async def change_presence(bot):
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Shape of You !"))
