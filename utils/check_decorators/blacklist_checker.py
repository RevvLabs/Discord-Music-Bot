
from discord.ext import commands
from utils.helper_function.unified_cache_manager import unified_cache

class UserBlacklisted(commands.CheckFailure):
    pass

def is_not_blacklisted():
    async def predicate(ctx: commands.Context):
        is_blacklisted = await unified_cache.is_user_blacklisted(ctx.author.id)
        if is_blacklisted:
            raise UserBlacklisted()
        return True
    return commands.check(predicate)
