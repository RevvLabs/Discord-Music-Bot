import os
from utils.bot_starter.load_commands import load_commands
from utils.bot_starter.load_events import load_events
from utils.bot_starter.load_owner_command import load_owner_commands


RED = "\033[31m"  
GREEN = "\033[32m"  
RESET = "\033[0m"  
YELLOW = "\033[33m"  
ORANGE = "\033[38;5;214m" 
SKYBLUE = "\033[38;5;75m"

async def load_cogs(bot):
   try:
      commands_loaded = await load_commands(bot, "cogs/commands", 0)
   except Exception as e:
      print(f"{RED}[ERROR]{RESET} Failed to load commands: {e}")
      commands_loaded = 0

   try:
      events_loaded = await load_events(bot, "cogs/events", 0)
   except Exception as e:
      print(f"{RED}[ERROR]{RESET} Failed to load events: {e}")
      events_loaded = 0

   try:
      owner_command_loaded = await load_owner_commands(bot, "cogs/owner_commands", 0)
   except Exception as e:
      print(f"{RED}[ERROR]{RESET} Failed to load owner commands: {e}")
      owner_command_loaded = 0

   total_commands = len([f for f in os.listdir("cogs/commands") if f.endswith(".py") and f != "__init__.py"])
   total_events = len([f for f in os.listdir("cogs/events") if f.endswith(".py") and f != "__init__.py"])
   total_owner = len([f for f in os.listdir("cogs/owner_commands") if f.endswith(".py") and f != "__init__.py"])

   print(f"\n{SKYBLUE}[COMMAND LOADER]{RESET} {commands_loaded}/{total_commands} command(s){RESET}")
   print(f"{SKYBLUE}[COMMAND LOADER]{RESET} {events_loaded}/{total_events} event(s){RESET}")
   print(f"{SKYBLUE}[COMMAND LOADER]{RESET} {owner_command_loaded}/{total_owner} owner-command(s){RESET}\n")
