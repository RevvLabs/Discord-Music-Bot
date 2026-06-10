import os

RED = "\033[31m"  
GREEN = "\033[32m"  
RESET = "\033[0m"  
YELLOW = "\033[33m"  
ORANGE = "\033[38;5;214m" 
SKYBLUE = "\033[38;5;75m"


async def load_owner_commands(bot, folder_path, loaded_count):
    owners_folder = folder_path
    for filename in os.listdir(owners_folder):
        if filename.endswith(".py") and filename != "__init__.py":
            cog_name = f"cogs.owner_commands.{filename[:-3]}"
            try:
                await bot.load_extension(cog_name)
                loaded_count += 1
                #print(f"{ORANGE}Loaded Owner Command: {cog_name}{RESET}")
            except Exception as e:
                print(f"{RED}[ERROR]{RESET} Failed to load owner command '{cog_name}': {e}")
    return loaded_count
