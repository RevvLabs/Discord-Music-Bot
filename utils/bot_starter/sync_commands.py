ORANGE = "\033[38;5;214m"
RESET = "\033[0m"

async def sync_commands(bot):
    try:
        synced = await bot.tree.sync()
        print(f"\n{ORANGE}[SLASH COMMAND]{RESET} Synced {len(synced)} command(s)\n")
    except Exception as e:
        print(f"Error syncing commands: {e}")
