"""
QueuePlacementView
==================
Shown when a user adds a single track while something is already playing.
Track is added to the END of queue immediately.
A "⚡ Play Next" button is shown for 60 seconds — if clicked, the track
is moved to the front of the queue. Otherwise it stays where it is.
"""
import discord

from utils.helper_function.bot_config import EMBED_COLOR
from utils.embed_designs import play as play_design


class QueuePlacementView(discord.ui.LayoutView):
    def __init__(self, player, track, requestor, duration: str, source: str, *, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.player = player
        self.track = track
        self.requestor = requestor
        self.duration = duration
        self.source = source
        self.message: discord.Message | None = None
        self._handled = False

        # Add to queue immediately — no waiting for user input
        player.metadata[track] = {"requestor": requestor, "source": source}
        player.queue.put(track)

        # Safety net: if playback stopped between search and here, start it
        if not player.playing and not player.queue.is_empty:
            import asyncio
            asyncio.create_task(self._start_playback())

        self._build()

    async def _start_playback(self):
        try:
            if self.player.paused:
                await self.player.pause(False)
            if not self.player.playing and not self.player.queue.is_empty:
                nxt = self.player.queue.get()
                await self.player.play(nxt, replace=True)
        except Exception:
            pass

    def _build(self):
        title = self.track.title or "Unknown"
        display_title = title[:25] + "…" if len(title) > 25 else title
        artist = getattr(self.track, "author", "") or "Unknown"
        artwork = getattr(self.track, "artwork", None)

        body = f"**{display_title}**\n{artist}\n{self.duration}"
        if artwork:
            content_item = discord.ui.Section(
                "## ✅ Added to Queue",
                body,
                f"Requested by {self.requestor.display_name}",
                accessory=discord.ui.Thumbnail(artwork),
            )
        else:
            content_item = discord.ui.TextDisplay(
                content=f"## ✅ Added to Queue\n{body}\n\nRequested by {self.requestor.display_name}"
            )

        container = discord.ui.Container(content_item, accent_color=EMBED_COLOR)
        self.add_item(container)

        row = discord.ui.ActionRow()
        play_next_btn = discord.ui.Button(
            label="⚡ Play Next",
            style=discord.ButtonStyle.success,
        )
        play_next_btn.callback = self._play_next
        row.add_item(play_next_btn)
        self.add_item(row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requestor.id:
            await interaction.response.send_message(
                "Only the person who requested this track can use this.", ephemeral=True
            )
            return False
        return True

    async def _play_next(self, interaction: discord.Interaction):
        if self._handled:
            await interaction.response.defer()
            return
        self._handled = True

        try:
            self.player.queue.remove(self.track, count=1)
            self.player.queue.put_at_front(self.track)
        except Exception:
            pass

        title = self.track.title or "Unknown"
        artist = getattr(self.track, "author", "") or "Unknown"
        artwork = getattr(self.track, "artwork", None)

        self.stop()
        await interaction.response.edit_message(
            view=play_design.play_next_added(title, artist, self.duration, artwork)
        )

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
