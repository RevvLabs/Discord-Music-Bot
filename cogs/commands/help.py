import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from utils.check_decorators.maintenance import maintenance_check
from utils.helper_function.unified_cache_manager import unified_cache

MAX_FIELD_LENGTH = 1024  
EXCLUDED_COMMANDS = ["forcefix", "jishaku", "help"] 
from utils.check_decorators.blacklist_checker import is_not_blacklisted
import os
from dotenv import load_dotenv
load_dotenv()
from utils.helper_function.bot_config import EMBED_COLOR, BOT_NAME
from utils.helper_function.auto_delete import schedule_delete

async def get_prefix(guild_id, bot_id=0):
    return await unified_cache.get_prefix(guild_id, bot_id)





COMMAND_INFO = {
    "favorite": {
        "description": "`Play all your favorite songs.`",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` fav `", "` f `"],
        "usage": "`-favorite`",
        "examples": [
            " -favorite",
            " -fav",
            " -f"
        ],
    },
    "fix": {
        "description": "`Fix the Player.`",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` fx `", "` fix `"],
        "usage": "`-fix`",
        "examples": [
            " -fix",
            " -fx"
        ],
           
    },
    "savefav": {
        "description": "`Save the currently playing song to your favorites.`",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` sf `", "` like `", "` save `", "` addfav `", "` af `", "` add `"],
        "usage": "`-savefav`",
        "examples": [
            " -savefav",
            " -sf",
            " -like",
            " -save",
            " -addfav",
            " -af",
            " -add"
        ],
    },
    "join": {
        "description": "` Joins the voice channel `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` j `"],
        "usage": "`-join`",
        "examples": [
            " -join",
            " -j"
        ],
    },
    "play": {
        "description": "` Plays a song `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` p `"],
        "usage": "`-play <song>`",
        "examples": [
            " -play example",
            " -p example",
            " -play https://open.spotify.com/track/example"
        ],
    },
    "dedicate": {
        "description": "`Dedicates and Plays a song to a mentioned user`",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` d `"],
        "usage": "`-dedicate @user <song>`",
        "examples": [
            " -dedicate @user example",
            " -d @user example",
            " -dedicate @user https://open.spotify.com/track/example"
        ],
    },
     "autoplay": {
        "description": "` Auto Plays toggle on or off `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` auto `"],
        "usage": "` -autoplay `",
        "examples": [
            " -autoplay ",
            " -ap ",
            " -auto "
        ],
    },
    "pause": {
        "description": "` Pauses the current song `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` ps `"],
        "usage": "`-pause`",
        "examples": [
            " -pause",
            " -ps"
        ],
    },
    "resume": {
        "description": "` Resumes the paused song `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` res `"],
        "usage": "`-resume`",
        "examples": [
            " -resume",
            " -r"
        ],
    },
    "skip": {
        "description": "` Skips the current song `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-skip`",
        "examples": [
            " -skip"
        ],
    },
    "previous": {
        "description": "` Goes to the previous song in the queue `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` prev `"],
        "usage": "`-previous`",
        "examples": [
            " -previous",
            " -prev"
        ],
    },
    "queue": {
        "description": "` Displays the current song queue `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` q `"],
        "usage": "`-queue`",
        "examples": [
            " -queue",
            " -q"
        ],
    },
    "nowplaying": {
        "description": "` Displays the current song playing `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` np `"],
        "usage": "`-nowplaying`",
        "examples": [
            " -nowplaying",
            " -np"
        ],
    },
    "remove": {
        "description": "` Removes a song from the queue `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` rm `"],
        "usage": "`-remove <song_number>`",
        "examples": [
            " -remove 3",
            " -rm 3"
        ],
    },
    "clearqueue": {
        "description": "` Clears the entire song queue `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` cq `"],
        "usage": "`-clearqueue`",
        "examples": [
            " -clearqueue",
            " -cq"
        ],
    },
    "shuffle": {
        "description": "` Shuffles the song queue `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` sh `"],
        "usage": "`-shuffle`",
        "examples": [
            " -shuffle",
            " -sh"
        ],
    },
    "replay": {
        "description": "` Replays the current song `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` rp `"],
        "usage": "`-replay`",
        "examples": [
            " -replay",
            " -rp"
        ],
    },
    "stop": {
        "description": "` Stops the current song and clears the queue `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` st `"],
        "usage": "`-stop`",
        "examples": [
            " -stop",
            " -st"
        ],
    },
    "disconnect": {
        "description": "` Disconnects the bot from the voice channel `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` dc `"],
        "usage": "`-disconnect`",
        "examples": [
            " -disconnect",
            " -dc"
        ],
    },
    "loop": {
        "description": "` Loops the current song `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` lp `"],
        "usage": "`-loop`",
        "examples": [
            " -loop",
            " -lp"
        ],
    },
    "search": {
        "description": "` Searches for a song `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` s `"],
        "usage": "`-search <song_name>`",
        "examples": [
            " -search example",
            " -s example"
        ],
    },
    "seek": {
        "description": "` Seeks to a specific time in the song `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` sk `"],
        "usage": "`-seek <time>`",
        "examples": [
            " -seek 1:30",
            " -sk 1:30"
        ],
    },
    
    "volume": {
        "description": "` Adjusts the bot's volume `",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` v `"],
        "usage": "`-volume <level>`",
        "examples": [
            " -volume 50",
            " -v 50"
        ],
    },
    
    "bassboost": {
        "description": "` Applies an Bass Boost audio filter `",
        "category": "` Filters `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-bassboost`",
        "examples": [
            " -bassboost"
        ],
    },
    "chipmunk": {
        "description": "` Applies a chipmunk voice filter `",
        "category": "` Filters `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-chipmunk`",
        "examples": [
            " -chipmunk"
        ],
    },
    "karaoke": {
        "description": "` Applies a karaoke voice filter `",
        "category": "` Filters `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-karaoke`",
        "examples": [
            " -karaoke"
        ],
    },
    "deepvoice": {
        "description": "` Applies a deep voice filter `",
        "category": "` Filters `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-deepvoice`",
        "examples": [
            " -deepvoice"
        ],
    },
    "nightcore": {
        "description": "` Applies a nightcore filter `",
        "category": "` Filters `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-nightcore`",
        "examples": [
            " -nightcore"
        ],
    },
    "tremolo": {
        "description": "` Applies a tremolo audio effect `",
        "category": "` Filters `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-tremolo`",
        "examples": [
            " -tremolo"
        ],
    },
    "vaporwave": {
        "description": "` Applies a vaporwave filter `",
        "category": "` Filters `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-vaporwave`",
        "examples": [
            " -vaporwave"
        ],
    },
    "reset": {
        "description": "` Resets all applied filters `",
        "category": "` Filters `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-reset`",
        "examples": [
            " -reset"
        ],
    },

    "ping": {
        "description": "` Checks the bot's latency `",
        "category": "` Info `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-ping`",
        "examples": [
            " -ping"
        ],
    },
    "leaderboard": {
        "description": "` Display's Leader board `",
        "category": "` Info `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` l `","` lb `"],
        "usage": "`-leaderboard`",
        "examples": [
            " -leaderboard",
            "-l",
            "-lb"
        ],
    },
    "profile": {
        "description": "` Display's your music profile card `",
        "category": "` Info `",
        "cooldown": "` 5 second(s) `",
        "aliases": [],
        "usage": "`-profile [@user]`",
        "examples": [
            " -profile",
            " -profile @someone"
        ],
    },
    "stats": {
        "description": "` Displays the bot's current statistics `",
        "category": "` Info `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` sts `"],
        "usage": "`-stats`",
        "examples": [
            " -stats"
            " -sts"
        ],
    },


    "engine": {
        "description": "` Choose your search engine.`",
        "category": "` Config `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` eng `"],
        "usage": "` -engine `",
        "examples": [
            " -engine ",
            " -eng "
        ],
    },
    "button": {
        "description": "` Toggle the visibility of the music control buttons.`",
        "category": "` Config `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` btn `"],
        "usage": "` -button `",
        "examples": [
            " -button ",
            " -btn "
        ],
    },
    "setup": {
        "description": "` setup channels for bot `",
        "category": "` Config `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "` -setup <text_channel> <voice_channel> `",
        "examples": [
            " -setup <text_channel> <voice_channel> ",
        ],
    },
    "getsetup": {
        "description": "` get setup channels for the Server `",
        "category": "` Config `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "` -getsetup `",
        "examples": [
            " -getsetup  ",
        ],
    },
    "clearsetup": {
        "description": "` clear setup channels for the server`",
        "category": "` Config `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "` -clearsetup  `",
        "examples": [
            " -clearsetup ",
        ],
    },
    "noprefixstatus": {
        "description": "`Check your no prefix access status and voting information`",
        "category": "` Vote `",
        "cooldown": "` 3 second(s) `",
        "aliases": [ "` prefixstatus `"],
        "usage": "`-noprefixstatus`",
        "examples": [
            " -noprefixstatus",
            " -prefixstatus"
        ],
    },
    "vote": {
        "description": "`Get voting information and no prefix access details`",
        "category": "` Vote `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` vote `"],
        "usage": "`-vote`",
        "examples": [
            " -vote"
        ],
    },
    "session": {
        "description": "`Lock or unlock the music session (DJ only)`",
        "category": "` DJ `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` sess `"],
        "usage": "`-session`",
        "examples": [
            " -session",
            " -sess"
        ],
    },
    "move": {
        "description": "`Move a track to a different position in the queue`",
        "category": "` DJ `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-move <from> <to>`",
        "examples": [
            " -move 3 1",
            " -move 5 2"
        ],
    },
    "loopqueue": {
        "description": "`Toggle queue loop mode on/off`",
        "category": "` Music `",
        "cooldown": "` 3 second(s) `",
        "aliases": ["` lq `", "` qloop `"],
        "usage": "`-loopqueue`",
        "examples": [
            " -loopqueue",
            " -lq"
        ],
    },
    "lyrics": {
        "description": "`Show lyrics for the current song or a search query`",
        "category": "` Music `",
        "cooldown": "` 5 second(s) `",
        "aliases": ["` None `"],
        "usage": "`-lyrics [query]`",
        "examples": [
            " -lyrics",
            " -lyrics Dior Shubh",
            " -lyrics Angli Ghumai Jaata Ne"
        ],
    },

}


class HelpDropdown(discord.ui.Select):
    def __init__(self, bot, author, parent_view=None):
        self.bot = bot
        self.author = author  
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label="Home",         description="Return to the Home menu."),
            discord.SelectOption(label="All Commands", description="Display all available commands."),
            discord.SelectOption(label="Music",        description="Music playback commands."),
            discord.SelectOption(label="DJ Commands",  description="Commands that require the DJ role."),
            discord.SelectOption(label="Filters",      description="Audio filter commands (DJ role required)."),
            discord.SelectOption(label="Info",         description="Information and profile commands."),
            discord.SelectOption(label="Utilities",    description="Useful utility commands."),
        ]
        super().__init__(placeholder="Choose a category to explore...", options=options)

    async def callback(self, interaction: discord.Interaction):

        if interaction.user != self.author:
            if not interaction.response.is_done():
                await interaction.response.send_message("You are not authorized to interact with this menu.", ephemeral=True)
            else:
                await interaction.followup.send("You are not authorized to interact with this menu.", ephemeral=True)
            return

        category = self.values[0]

        if category == "Home":
            content = "## Help Menu\n"
            content += "Explore the available categories to find the commands you need.\n\n"
            content += "**Available Categories:**\n- Music\n- DJ Commands *(DJ role required)*\n- Filters *(DJ role required)*\n- Info\n- Utilities\n\n"
            content += f"*For admin & owner commands use `/adminhelp`*\n"
            content += "*Select a category from the dropdown menu below.*"
            await self.parent_view.update_content(interaction, content)
            return

        if category == "Music":
            commands_list = [
                {"name": "join",        "description": "Join the voice channel"},
                {"name": "play",        "description": "Play a song or playlist"},
                {"name": "pause",       "description": "Pause the current song"},
                {"name": "resume",      "description": "Resume the paused song"},
                {"name": "skip",        "description": "Skip the current song (vote or instant for DJs)"},
                {"name": "previous",    "description": "Go back to the previous song"},
                {"name": "queue",       "description": "Display the current song queue"},
                {"name": "nowplaying",  "description": "Show the currently playing song"},
                {"name": "remove",      "description": "Remove a song from the queue"},
                {"name": "clearqueue",  "description": "Clear the entire song queue"},
                {"name": "replay",      "description": "Replay the current song from the start"},
                {"name": "stop",        "description": "Stop music and disconnect the bot"},
                {"name": "disconnect",  "description": "Disconnect the bot from the voice channel"},
                {"name": "loop",        "description": "Cycle loop mode: off → track → queue"},
                {"name": "loopqueue",   "description": "Toggle queue loop on/off"},
                {"name": "search",      "description": "Search for a song and pick from results"},
                {"name": "seek",        "description": "Seek to a specific time in the current song"},
                {"name": "volume",      "description": "Adjust the playback volume"},
                {"name": "favorite",    "description": "Play all your saved favourite songs"},
                {"name": "savefav",     "description": "Save the current song (or queue) to favourites"},
                {"name": "autoplay",    "description": "Toggle autoplay on/off"},
                {"name": "playlist",    "description": "Manage your personal playlists"},
                {"name": "history",     "description": "Show the last 10 tracks played this session"},
                {"name": "lyrics",      "description": "Show lyrics for the current song or a search query"},
            ]
            content = "## Music Commands\n"
            content += "General music playback commands available to everyone.\n\n"
            for cmd in commands_list:
                content += f"`{cmd['name']}` — {cmd['description']}\n"
            content += "\n*If the session is locked by a DJ, ask them to unlock it or add you via `/sessionadd @you`.*\n"
            content += "*Use the dropdown menu to navigate.*"
            await self.parent_view.update_content(interaction, content)
            return

        if category == "DJ Commands":
            commands_list = [
                {"name": "session",       "description": "Lock (🔒 private) or unlock (🔓 public) the music session — blocks all non-DJ users when locked"},
                {"name": "sessionadd",    "description": "Add a specific user to your locked session so they can use music commands"},
                {"name": "sessionremove", "description": "Remove a previously added user from your locked session"},
                {"name": "shuffle",       "description": "Shuffle the current queue"},
                {"name": "move",          "description": "Move a track to a different position in the queue"},
                {"name": "engine",        "description": "Choose your personal search engine (YouTube, Spotify, etc.)"},
                {"name": "dedicate",      "description": "Dedicate a song to someone in the voice channel"},
            ]
            content = "## DJ Commands\n"
            content += "Require the **DJ role** by default. Admins can adjust this via `/djlock` & `/djunlock`.\n\n"
            for cmd in commands_list:
                content += f"`{cmd['name']}` — {cmd['description']}\n"
            content += "\n**Session system:**\n"
            content += "When a DJ locks the session, all regular users are blocked from music commands.\n"
            content += "The DJ can grant access to specific users with `/sessionadd @user`.\n"
            content += "Added users can use basic music commands — DJ-locked commands still require the DJ role.\n"
            content += "\n*Use the dropdown menu to navigate.*"
            await self.parent_view.update_content(interaction, content)
            return

        if category == "Filters":
            commands_list = [
                {"name": "bassboost", "description": "Toggle Bass Boost filter"},
                {"name": "nightcore", "description": "Toggle Nightcore filter"},
                {"name": "vaporwave", "description": "Toggle Vaporwave filter"},
                {"name": "karaoke",   "description": "Toggle Karaoke filter"},
                {"name": "8d",        "description": "Toggle 8D Audio filter"},
                {"name": "chipmunk",  "description": "Toggle Chipmunk filter"},
                {"name": "deepvoice", "description": "Toggle Deep Voice filter"},
                {"name": "reset",     "description": "Reset all active filters"},
            ]
            content = "## Filter Commands\n"
            content += "Audio filters — require the **DJ role** by default.\nServer admins can unlock filters for everyone via `/djunlock`.\n\n"
            for cmd in commands_list:
                content += f"`{cmd['name']}` — {cmd['description']}\n"
            content += "\n*Use the dropdown menu to navigate.*"
            await self.parent_view.update_content(interaction, content)
            return

        if category == "Info":
            commands_list = [
                {"name": "help",        "description": "Show the help menu"},
                {"name": "adminhelp",   "description": "Show admin & owner commands"},
                {"name": "leaderboard", "description": "Display the server leaderboard"},
                {"name": "profile",     "description": "View your music profile card"},
                {"name": "ping",        "description": "Show bot, API, and database latency"},
                {"name": "stats",       "description": "Display bot statistics"},
            ]
            content = "## Info Commands\n"
            content += "Informational commands available to everyone.\n\n"
            for cmd in commands_list:
                content += f"`{cmd['name']}` — {cmd['description']}\n"
            content += "\n*Use the dropdown menu to navigate.*"
            await self.parent_view.update_content(interaction, content)
            return

        if category == "Utilities":
            commands_list = [
                {"name": "fix",      "description": "Fix the bot's voice connection"},
                {"name": "djlockstatus", "description": "Show which commands are DJ-locked in this server"},
            ]
            content = "## Utilities\n"
            content += "General-purpose commands.\n\n"
            for cmd in commands_list:
                content += f"`{cmd['name']}` — {cmd['description']}\n"
            content += "\n*Use the dropdown menu to navigate.*"
            await self.parent_view.update_content(interaction, content)
            return

        if category == "All Commands":
            all_commands = {
                "Music [24]":       ["join","play","pause","resume","skip","previous","queue","nowplaying","remove","clearqueue","replay","stop","disconnect","loop","loopqueue","search","seek","volume","favorite","savefav","autoplay","playlist","history","lyrics"],
                "DJ Commands [7]":  ["session","sessionadd","sessionremove","shuffle","move","engine","dedicate"],
                "Filters [8]":      ["bassboost","nightcore","vaporwave","karaoke","8d","chipmunk","deepvoice","reset"],
                "Info [6]":         ["help","adminhelp","leaderboard","profile","ping","stats"],
                "Utilities [2]":    ["fix","djlockstatus"],
            }
            content = "## All Available Commands\n\n"
            total_commands = 0
            for cat_name, cmds in all_commands.items():
                total_commands += len(cmds)
                content += f"**{cat_name}**\n" + " ".join([f"`{c}`" for c in cmds]) + "\n\n"
            content += f"*{total_commands} commands • Use `/adminhelp` for admin & owner commands • {BOT_NAME}*"
            await self.parent_view.update_content(interaction, content)
            return
        else:
            cog = self.bot.get_cog(category)
            if not cog:
                msg = f"Category `{category}` not found."
                if not interaction.response.is_done():
                    await interaction.response.send_message(msg, ephemeral=True)
                else:
                    await interaction.followup.send(msg, ephemeral=True)
                return
            commands_list = [command for command in cog.get_commands() if command.name not in EXCLUDED_COMMANDS]

            content = f"## {category} Commands\n"
            content += f"Explore the commands available in the `{category}` category.\n\n"

            if commands_list:
                for command in commands_list:
                    content += f"`{command.name}` - {command.description or 'No description available.'}\n"
            else:
                content += "No commands available in this category."

            content += "\n*Use the dropdown menu to navigate.*"
            
            await self.parent_view.update_content(interaction, content)

class HelpDropdownView(discord.ui.LayoutView):
    def __init__(self, bot, author, content="Select a category to begin.", message=None):
        super().__init__()
        self.timeout = 60
        self.bot = bot
        self.author = author
        self.message = message  
        
        self.display = discord.ui.TextDisplay(content=content)
        self.container = discord.ui.Container(self.display, accent_color=EMBED_COLOR)
        
        self.row = discord.ui.ActionRow()
        self.dropdown = HelpDropdown(bot, author, parent_view=self)
        self.row.add_item(self.dropdown)
        
        self.add_item(self.container)
        self.add_item(self.row)

    async def update_content(self, interaction: discord.Interaction, content: str):
        self.display.content = content
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        if self.message:
            try:
                v = discord.ui.LayoutView()
                v.add_item(discord.ui.Container(
                    discord.ui.TextDisplay(content="⏳ Closed — inactive for too long."),
                    accent_color=discord.Color.from_rgb(128, 128, 128),
                ))
                await self.message.edit(view=v)
            except Exception:
                pass

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="Displays the help menu with available categories and commands.")
    @commands.cooldown(1, 3, BucketType.user)
    @maintenance_check()
    @is_not_blacklisted()
    async def help_command(self, ctx, *, command_name=None):
        try:
            guild_id = ctx.guild.id
            prefix = await get_prefix(guild_id, ctx.bot.user.id)
            
            if command_name:
                command_info = COMMAND_INFO.get(command_name)
                if command_info:
                    examples = "\n".join([example.replace('-', prefix, 1) for example in command_info['examples']])
                    embed = discord.Embed(
                        title=f"Help: {command_name}",
                        color=EMBED_COLOR,
                    )
                    embed.add_field(name="Description", value=command_info['description'], inline=False)
                    embed.add_field(name="Category",    value=command_info['category'],    inline=True)
                    embed.add_field(name="Cooldown",    value=command_info['cooldown'],    inline=True)
                    embed.add_field(name="Aliases",     value=', '.join(command_info['aliases']), inline=False)
                    embed.add_field(name="Usage",       value=command_info['usage'].replace('-', prefix, 1), inline=False)
                    embed.add_field(name="Examples",    value=f"```{examples}```",         inline=False)
                    schedule_delete(await ctx.send(embed=embed))
                else:
                    embed = discord.Embed(
                        description=f"Command `{command_name}` not found.",
                        color=EMBED_COLOR,
                    )
                    schedule_delete(await ctx.send(embed=embed))
            else:
                content = "## Help Menu\n"
                content += "Explore the available categories to find the commands you need.\n\n"
                content += "**Available Categories:**\n"
                content += "- Music\n"
                content += "- DJ Commands *(DJ role required)*\n"
                content += "- Filters *(DJ role required)*\n"
                content += "- Info\n"
                content += "- Utilities\n\n"
                content += "*For admin & owner commands use `/adminhelp`*\n"
                content += "*Select a category from the dropdown menu below.*"

                view = HelpDropdownView(self.bot, ctx.author, content=content)
                message = await ctx.send(view=view)  
                view.message = message

        except Exception as e:
            import traceback
            traceback.print_exc()
            v = discord.ui.LayoutView()
            v.add_item(discord.ui.Container(
                discord.ui.TextDisplay(content=f"> An error occurred: {str(e)}"),
                accent_color=EMBED_COLOR,
            ))
            schedule_delete(await ctx.send(view=v))


async def setup(bot):
    await bot.add_cog(Help(bot))
