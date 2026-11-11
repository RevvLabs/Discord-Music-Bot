import asyncio
import logging
import os
import voltricx
from dotenv import load_dotenv
from utils.colours.colours import (
    RESET, GREEN, RED, CYAN, BRIGHT_YELLOW, BRIGHT_GREEN, BRIGHT_RED, NEON_PURPLE, BLUE
)
from utils.logger.mewzik_logger import bot_logger

# Surface voltricx's internal logger.error messages to the console so node
# connection failures (auth errors, wrong port, wrong Lavalink version, etc.)
# are visible at startup instead of being silently dropped.
logging.basicConfig(
    level=logging.WARNING,
    format="%(name)s %(levelname)s: %(message)s",
)

load_dotenv()

CACHE_CAPACITY = int(os.getenv("CACHE_CAPACITY", 1024))


def _load_nodes() -> list[voltricx.Node]:
    """Build the list of Node objects from environment variables."""
    nodes: list[voltricx.Node] = []

    # Try numbered multi-node format first
    index = 1
    while True:
        uri = os.getenv(f"NODE_{index}_URI")
        password = os.getenv(f"NODE_{index}_PASSWORD")

        if not uri or not password:
            break

        region = os.getenv(f"NODE_{index}_REGION") or "global"
        nodes.append(
            voltricx.NodeConfig(
                uri=uri,
                password=password,
                region=region,
                identifier=f"node-{index}" + (f"-{region}" if region != "global" else ""),
            )
        )
        index += 1

    # Fall back to legacy single-node env vars
    if not nodes:
        uri = os.getenv("URI")
        password = os.getenv("PASSWORD")
        if uri and password:
            nodes.append(voltricx.NodeConfig(uri=uri, password=password, identifier="default"))

    return nodes


async def connect_to_lavalink(self) -> None:
    try:
        node_configs = _load_nodes()

        if not node_configs:
            print(
                f"{BRIGHT_RED}[ERROR] Lavalink Config Missing{RESET}: "
                "No nodes found. Set URI + PASSWORD, or NODE_1_URI + NODE_1_PASSWORD."
            )
            if bot_logger.enabled:
                bot_logger.error(
                    "Lavalink configuration missing — no nodes found",
                    hint="Set NODE_1_URI + NODE_1_PASSWORD (or legacy URI + PASSWORD) in .env",
                )
            return

        if bot_logger.enabled:
            for config in node_configs:
                bot_logger.outgoing(
                    "Lavalink node connection attempt",
                    node_id=config.identifier,
                    uri=config.uri,
                    region=config.region or "global",
                )

        nodes = {}
        try:
            with bot_logger.timer() as t:
                # Pool.connect in 1.0.5 takes client and nodes (Iterable[NodeConfig])
                # cache_config is used to initialize the HyperCache system.
                await voltricx.Pool.connect(
                    client=self, 
                    nodes=node_configs, 
                    cache_config={'capacity': 1000},
                    default_search_source="dzsearch"
                )

            # In 1.0.5, Pool.connect awaits node.connect() which is already mostly ready
            # but we can keep a short wait for the READY op if preferred.
            # However, Pool.connect in 1.0.5 actually awaits node.connect() which 
            # awaits the websocket connection.
            
            # Nodes are now waited for in Pool.connect
            nodes = voltricx.Pool.nodes()

            if bot_logger.enabled:
                for node in nodes.values():
                    is_ok = node.status == voltricx.NodeStatus.connected
                    if is_ok:
                        bot_logger.incoming(
                            "Lavalink node connected",
                            node_id=node.identifier,
                            uri=node.uri,
                            region=node.config.region or "global",
                            status="CONNECTED",
                            elapsed_ms=t.elapsed_ms,
                        )
                    else:
                        bot_logger.error(
                            "Lavalink node failed to connect",
                            node_id=node.identifier,
                            uri=node.uri,
                            region=node.config.region or "global",
                            status="FAILED",
                        )

        except voltricx.InvalidNodeException as e:
            print(f"{BRIGHT_RED}[ERROR] Invalid Node Exception{RESET}: {e}")
            if bot_logger.enabled:
                bot_logger.error("Lavalink invalid node exception", error=str(e))
        except voltricx.AuthorizationFailedException as e:
            print(f"{BRIGHT_RED}[ERROR] Lavalink Authentication Error{RESET}: {e}")
            if bot_logger.enabled:
                bot_logger.error("Lavalink authentication failed", error=str(e))
        except voltricx.NodeException as e:
            print(f"{BRIGHT_RED}[ERROR] Lavalink Connection Error{RESET}: {e}")
            if bot_logger.enabled:
                bot_logger.error("Lavalink node exception", error=str(e))
        except Exception as e:
            print(f"{BRIGHT_RED}[ERROR] Lavalink General Error{RESET}: {e}")
            if bot_logger.enabled:
                bot_logger.error("Lavalink general connection error", error=str(e))
        finally:
            print(f"{BRIGHT_YELLOW}[Lavalink]{RESET} Ready to handle audio playback.\n")
            if bot_logger.enabled:
                connected_nodes = [n for n in nodes.values() if n.status == voltricx.NodeStatus.connected]
                bot_logger.info(
                    "Lavalink pool ready",
                    connected=len(connected_nodes),
                    total=len(nodes),
                )

    except Exception as e:
        print(f"{BRIGHT_RED}[ERROR] Lavalink Setup Error{RESET}: {e}")
        if bot_logger.enabled:
            bot_logger.error("Lavalink setup raised unexpected error", error=str(e))
