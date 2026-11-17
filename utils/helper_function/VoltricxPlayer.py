import discord
import voltricx
from voltricx.player import Player
from utils.logger.mewzik_logger import bot_logger


class LavaMusic(Player):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        super().__init__(client, channel)
        self.metadata = {}
        # Idle auto-disconnect: with no timeout set, voltricx never fires
        # on_voltricx_inactive_player, so the bot would sit in the VC forever.
        # 300s of nothing playing → inactive event → disconnect (skipped for 24/7).
        self.inactive_timeout = 300
        self._autoplay = voltricx.AutoPlayMode.partial
        self.source = "ytsearch"
        self.status = True
        self.filter_status = False
        self.filter_name = None
        self._volume = 60
        # Music-session lifecycle (see utils/helper_function/music_session.py).
        self.session_active = False
        self.msg = None  # current now-playing card message
        self._destroy_dispatched = False

        if bot_logger.enabled:
            guild_id = getattr(self.guild, "id", "unknown") if self.guild else "unknown"
            node_id = getattr(self.node, "identifier", "unknown") if self.node else "unknown"
            node_uri = getattr(self.node, "uri", "unknown") if self.node else "unknown"
            bot_logger.info(
                "LavaMusic player initialised",
                guild_id=guild_id,
                node_id=node_id,
                node_uri=node_uri,
                volume=self.volume,
                source=self.source,
            )

    def cleanup(self) -> None:
        # voltricx calls cleanup() at the end of every player teardown: /stop,
        # /disconnect, being kicked/moved out, failed voice reconnect. Once the
        # player is gone Lavalink's TrackEnd can no longer reach on_voltricx_track_end,
        # so this event is the only reliable "player is gone" signal. Teardown can
        # run twice (disconnect() + the resulting voice-state update) — dispatch once.
        super().cleanup()
        if not self._destroy_dispatched:
            self._destroy_dispatched = True
            self.client.dispatch("mewzik_player_destroyed", self)

    def check_queue_size(self) -> bool:
        current = len(self.queue)
        if bot_logger.enabled:
            bot_logger.debug(
                "Queue size check",
                current=current,
                max=100,
                ok=current < 100,
            )
        return current < 100
