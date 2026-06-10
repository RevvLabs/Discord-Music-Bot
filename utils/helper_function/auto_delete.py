import asyncio
import discord


async def _delete_after(message, delay: float) -> None:
    await asyncio.sleep(delay)
    try:
        # slash command ctx.send() returns InteractionCallbackResponse, not Message
        if hasattr(message, "delete"):
            await message.delete()
        elif hasattr(message, "delete_original_response"):
            await message.delete_original_response()
        elif hasattr(message, "resolve"):
            resolved = await message.resolve()
            await resolved.delete()
    except (discord.NotFound, discord.HTTPException, discord.Forbidden, AttributeError):
        pass


# Strong references — asyncio only keeps weak refs to tasks, so without this
# a pending delete task can be garbage-collected mid-sleep and never fire.
_pending_tasks: set = set()


def schedule_delete(message, delay: float = 60.0) -> None:
    task = asyncio.create_task(_delete_after(message, delay))
    _pending_tasks.add(task)
    task.add_done_callback(_pending_tasks.discard)
