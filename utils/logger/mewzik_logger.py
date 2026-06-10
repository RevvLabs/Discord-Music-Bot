"""
Mewzik Bot — Real-time Async Logging System
============================================

Configure entirely through environment variables — no code changes needed:

  LOG_ENABLED           = true           # Master on/off switch        (default: true)
  LOG_LEVEL             = INFO           # DEBUG | INFO | WARNING | ERROR  (default: INFO)
  LOG_DEBUG             = false          # Shortcut to force DEBUG level    (default: false)
  LOG_FORMAT            = structured     # structured | simple | json       (default: structured)
  LOG_TO_FILE           = false          # Mirror output to a rotating file (default: false)
  LOG_FILE_PATH         = logs/mewzik.log
  LOG_FILE_MAX_BYTES    = 10485760       # 10 MB per file                   (default: 10485760)
  LOG_FILE_BACKUP_COUNT = 5              # rotated copies to keep           (default: 5)
  LOG_MASK_SENSITIVE    = true           # hide tokens/passwords in output  (default: true)
  LOG_SENSITIVE_KEYS    = token,password,secret,key,auth,webhook

Design
------
* Zero decorators — callers use:   if bot_logger.enabled: ...
* Console output calls print() directly — stdout writes are microseconds,
  never a meaningful blocker for the asyncio event loop.
* File I/O is handled by a background daemon thread draining a queue,
  so disk writes never touch the event loop at all.
* Single singleton `bot_logger` exported at module level.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import queue
import re
import threading
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Configuration (read once at import time)
# ──────────────────────────────────────────────────────────────────────────────

LOG_ENABLED: bool = os.getenv("LOG_ENABLED", "true").strip().lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()
LOG_DEBUG: bool = os.getenv("LOG_DEBUG", "false").strip().lower() == "true"
LOG_FORMAT: str = os.getenv("LOG_FORMAT", "structured").strip().lower()
LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "false").strip().lower() == "true"
LOG_FILE_PATH: str = os.getenv("LOG_FILE_PATH", "logs/mewzik.log").strip()
LOG_FILE_MAX_BYTES: int = int(os.getenv("LOG_FILE_MAX_BYTES", str(10 * 1024 * 1024)))
LOG_FILE_BACKUP_COUNT: int = int(os.getenv("LOG_FILE_BACKUP_COUNT", "5"))
LOG_MASK_SENSITIVE: bool = os.getenv("LOG_MASK_SENSITIVE", "true").strip().lower() == "true"
LOG_SENSITIVE_KEYS: list[str] = [
    k.strip()
    for k in os.getenv(
        "LOG_SENSITIVE_KEYS", "token,password,secret,key,auth,webhook"
    ).split(",")
    if k.strip()
]

# Effective numeric level used to gate emissions
_EFFECTIVE_LEVEL: int = (
    logging.DEBUG
    if (LOG_DEBUG or LOG_LEVEL == "DEBUG")
    else getattr(logging, LOG_LEVEL, logging.INFO)
)

# ──────────────────────────────────────────────────────────────────────────────
# ANSI colour palette
# ──────────────────────────────────────────────────────────────────────────────

_C: dict[str, str] = {
    "RESET":    "\033[0m",
    "DEBUG":    "\033[36m",      # Cyan
    "INFO":     "\033[32m",      # Green
    "WARNING":  "\033[33m",      # Yellow
    "ERROR":    "\033[91m",      # Bright Red
    "CRITICAL": "\033[91;1m",    # Bold Bright Red
    "INCOMING": "\033[94m",      # Bright Blue   (user → bot)
    "OUTGOING": "\033[95m",      # Magenta        (bot → server / API)
    "SYSTEM":   "\033[37m",      # Light Gray
    "DEBUG_C":  "\033[36m",      # Cyan  (category label for debug lines)
    "TS":       "\033[90m",      # Dark Gray (timestamp)
    "META":     "\033[90m",      # Dark Gray (key=value pairs)
}

_ARROWS: dict[str, str] = {
    "INCOMING": "←",
    "OUTGOING": "→",
}

# ──────────────────────────────────────────────────────────────────────────────
# Sensitive-data masking
# ──────────────────────────────────────────────────────────────────────────────

_URL_PWD_RE: re.Pattern = re.compile(r"(://[^:]+:)([^@\s]+)(@)")
_KEY_PATTERNS: dict[str, re.Pattern] = {
    k: re.compile(
        rf'({re.escape(k)}[\s"]*[:=][\s"]*)([^\s"&,}}\]\n]+)',
        re.IGNORECASE,
    )
    for k in LOG_SENSITIVE_KEYS
}


def _mask(text: str) -> str:
    """Return *text* with passwords / tokens replaced by ***."""
    if not LOG_MASK_SENSITIVE:
        return text
    text = _URL_PWD_RE.sub(r"\1***\3", text)
    for pattern in _KEY_PATTERNS.values():
        text = pattern.sub(r"\1***", text)
    return text


# ──────────────────────────────────────────────────────────────────────────────
# Background file-writer thread (non-blocking file I/O)
# ──────────────────────────────────────────────────────────────────────────────

_file_queue: queue.Queue | None = None
_file_handler: logging.handlers.RotatingFileHandler | None = None


def _file_writer_loop(q: queue.Queue, handler: logging.handlers.RotatingFileHandler) -> None:
    """Daemon thread: drain the queue and write each line to the rotating file."""
    while True:
        item = q.get()
        if item is None:   # sentinel → stop
            break
        level_num, line = item
        record = logging.LogRecord(
            name="mewzik", level=level_num,
            pathname="", lineno=0,
            msg=line, args=(), exc_info=None,
        )
        try:
            handler.emit(record)
        except Exception:
            pass


def _init_file_logging() -> None:
    global _file_queue, _file_handler
    if not LOG_TO_FILE:
        return
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    _file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )
    _file_handler.setLevel(_EFFECTIVE_LEVEL)
    _file_handler.setFormatter(logging.Formatter("%(message)s"))
    _file_queue = queue.Queue(maxsize=10_000)
    t = threading.Thread(
        target=_file_writer_loop,
        args=(_file_queue, _file_handler),
        daemon=True,
        name="mewzik-file-logger",
    )
    t.start()


_init_file_logging()

# ──────────────────────────────────────────────────────────────────────────────
# Formatting
# ──────────────────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _fmt_structured(level: str, category: str, message: str, meta: dict) -> str:
    ts = _ts()
    col_level = _C.get(level, _C["INFO"])
    col_cat = _C.get(category, _C["SYSTEM"])
    reset = _C["RESET"]
    arrow = _ARROWS.get(category, "•")

    meta_parts = [f"{k}={_mask(str(v))}" for k, v in meta.items()]
    meta_str = (
        f"  {_C['META']}{' | '.join(meta_parts)}{reset}" if meta_parts else ""
    )

    return (
        f"{_C['TS']}[{ts}]{reset} "
        f"{col_level}[{level:>8}]{reset} "
        f"{col_cat}[{arrow} {category}]{reset} "
        f"{_mask(message)}{meta_str}"
    )


def _fmt_simple(level: str, category: str, message: str, meta: dict) -> str:
    ts = _ts()
    meta_str = (
        " | " + " | ".join(f"{k}={_mask(str(v))}" for k, v in meta.items())
        if meta
        else ""
    )
    return f"[{ts}] [{level}] [{category}] {_mask(message)}{meta_str}"


def _fmt_json(level: str, category: str, message: str, meta: dict) -> str:
    entry: dict = {
        "timestamp": _ts(),
        "level": level,
        "category": category,
        "message": _mask(message),
        **{k: _mask(str(v)) for k, v in meta.items()},
    }
    return json.dumps(entry, ensure_ascii=False)


_FORMATTERS = {
    "structured": _fmt_structured,
    "simple": _fmt_simple,
    "json": _fmt_json,
}


def _format(level: str, category: str, message: str, meta: dict) -> tuple[str, str]:
    """Return (terminal_line_with_ansi, plain_file_line)."""
    fmt_fn = _FORMATTERS.get(LOG_FORMAT, _fmt_structured)
    terminal = fmt_fn(level, category, message, meta)
    file_line = _fmt_simple(level, category, message, meta)
    return terminal, file_line


# ──────────────────────────────────────────────────────────────────────────────
# Core emit — always runs synchronously
#
# Why not run_in_executor?
#   print() writes to a libc-buffered stream; with flush=True the syscall
#   completes in microseconds — no meaningful event-loop stall.
#   Using run_in_executor silently swallows exceptions inside the Future
#   which is what caused logs to disappear.
# ──────────────────────────────────────────────────────────────────────────────

def _level_num(level: str) -> int:
    return getattr(logging, level, logging.INFO)


def _emit(level: str, category: str, message: str, meta: dict) -> None:
    """Synchronous emit. Safe to call from async code — print() is fast."""
    if not LOG_ENABLED:
        return
    if _level_num(level) < _EFFECTIVE_LEVEL:
        return

    terminal, file_line = _format(level, category, message, meta)

    # Console — direct, immediate, always visible
    try:
        print(terminal, flush=True)
    except Exception:
        pass

    # File — queued to background thread (non-blocking)
    if _file_queue is not None:
        try:
            _file_queue.put_nowait((_level_num(level), file_line))
        except queue.Full:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Request timer — lightweight perf measurement for outgoing calls
# ──────────────────────────────────────────────────────────────────────────────

class RequestTimer:
    """Sync context manager for measuring elapsed time.

    Usage::

        with bot_logger.timer() as t:
            result = await some_api_call()
        # t.elapsed_ms is available immediately after the with block
    """

    elapsed_ms: float = 0.0

    def __enter__(self) -> "RequestTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_) -> None:
        self.elapsed_ms = round((time.perf_counter() - self._start) * 1000, 2)

    def __repr__(self) -> str:
        return f"{self.elapsed_ms}ms"


# ──────────────────────────────────────────────────────────────────────────────
# Public API — MewzikLogger singleton
# ──────────────────────────────────────────────────────────────────────────────

class MewzikLogger:
    """
    Structured logger for Mewzik Bot.

    All methods call _emit() synchronously. print() is fast enough
    that there is no meaningful event-loop stall. File I/O is handled
    by a background daemon thread.

    Caller pattern (no decorators required)::

        from utils.logger.mewzik_logger import bot_logger

        if bot_logger.enabled:
            await bot_logger.async_incoming(
                "play command received",
                user_id=ctx.author.id,
                query=query,
            )

    The async_* variants exist as a convenience (they are just the sync
    variants wrapped in a coroutine so they can be awaited if desired).
    """

    def __init__(self) -> None:
        self.enabled: bool = LOG_ENABLED
        self.debug_mode: bool = LOG_DEBUG or (LOG_LEVEL == "DEBUG")

    @staticmethod
    def timer() -> RequestTimer:
        return RequestTimer()

    # ── INCOMING  (user → bot) ────────────────────────────────────────────────

    def incoming(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("INFO", "INCOMING", message, meta)

    async def async_incoming(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("INFO", "INCOMING", message, meta)

    # ── OUTGOING  (bot → Lavalink / Discord API / external) ──────────────────

    def outgoing(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("INFO", "OUTGOING", message, meta)

    async def async_outgoing(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("INFO", "OUTGOING", message, meta)

    # ── INFO ──────────────────────────────────────────────────────────────────

    def info(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("INFO", "SYSTEM", message, meta)

    async def async_info(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("INFO", "SYSTEM", message, meta)

    # ── DEBUG ─────────────────────────────────────────────────────────────────

    def debug(self, message: str, **meta) -> None:
        if self.enabled and self.debug_mode:
            _emit("DEBUG", "DEBUG_C", message, meta)

    async def async_debug(self, message: str, **meta) -> None:
        if self.enabled and self.debug_mode:
            _emit("DEBUG", "DEBUG_C", message, meta)

    # ── WARNING ───────────────────────────────────────────────────────────────

    def warning(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("WARNING", "SYSTEM", message, meta)

    async def async_warning(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("WARNING", "SYSTEM", message, meta)

    # ── ERROR ─────────────────────────────────────────────────────────────────

    def error(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("ERROR", "ERROR", message, meta)

    async def async_error(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("ERROR", "ERROR", message, meta)

    # ── CRITICAL ──────────────────────────────────────────────────────────────

    def critical(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("CRITICAL", "ERROR", message, meta)

    async def async_critical(self, message: str, **meta) -> None:
        if self.enabled:
            _emit("CRITICAL", "ERROR", message, meta)


# ──────────────────────────────────────────────────────────────────────────────
# Singleton — import this everywhere
# ──────────────────────────────────────────────────────────────────────────────

bot_logger = MewzikLogger()
