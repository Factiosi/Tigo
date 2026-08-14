"""Always-on debug journal with 1-hour retention."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable

from src.core.paths import app_data_root, debug_log_path

_RETENTION = timedelta(hours=1)
_listeners: list[Callable[[], None]] = []
_lines: list["DebugLogEntry"] = []
_lock = threading.RLock()
_LINE_PREFIX = re.compile(
    r"^\[(?P<ts>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})\]\s+\[(?P<source>[^\]]+)\]\s+\[(?P<level>[^\]]+)\]\s+(?P<message>.*)$"
)


class DebugLogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass(frozen=True)
class DebugLogEntry:
    timestamp: datetime
    source: str
    level: DebugLogLevel
    message: str

    @property
    def formatted(self) -> str:
        ts = self.timestamp.strftime("%d.%m.%Y %H:%M:%S")
        return f"[{ts}] [{self.source}] [{self.level.value}] {self.message}"


def subscribe(listener: Callable[[], None]) -> None:
    with _lock:
        _listeners.append(listener)


def unsubscribe(listener: Callable[[], None]) -> None:
    with _lock:
        if listener in _listeners:
            _listeners.remove(listener)


def _notify() -> None:
    for listener in list(_listeners):
        try:
            listener()
        except Exception:
            pass


def _purge_old() -> None:
    cutoff = datetime.now() - _RETENTION
    while _lines and _lines[0].timestamp < cutoff:
        _lines.pop(0)


def _parse_line(line: str) -> DebugLogEntry | None:
    match = _LINE_PREFIX.match(line.strip())
    if not match:
        return None
    try:
        timestamp = datetime.strptime(match.group("ts"), "%d.%m.%Y %H:%M:%S")
    except ValueError:
        return None
    level_raw = match.group("level")
    try:
        level = DebugLogLevel(level_raw)
    except ValueError:
        level = DebugLogLevel.INFO
    return DebugLogEntry(
        timestamp=timestamp,
        source=match.group("source"),
        level=level,
        message=match.group("message"),
    )


def _append_persistent(entry: DebugLogEntry) -> None:
    app_data_root().mkdir(parents=True, exist_ok=True)
    path = debug_log_path()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry.formatted + "\n")


def _load_persistent_entries() -> list[DebugLogEntry]:
    path = debug_log_path()
    if not path.exists():
        return []
    cutoff = datetime.now() - _RETENTION
    entries: list[DebugLogEntry] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        entry = _parse_line(line)
        if entry and entry.timestamp >= cutoff:
            entries.append(entry)
    return entries


def _rewrite_persistent(entries: list[DebugLogEntry]) -> None:
    app_data_root().mkdir(parents=True, exist_ok=True)
    path = debug_log_path()
    text = "\n".join(entry.formatted for entry in entries)
    if text:
        path.write_text(text + "\n", encoding="utf-8")
    elif path.exists():
        path.write_text("", encoding="utf-8")


def debug(source: str, message: str, *, level: str = "info") -> None:
    try:
        log_level = DebugLogLevel(level)
    except ValueError:
        log_level = DebugLogLevel.INFO
    entry = DebugLogEntry(datetime.now(), source, log_level, message.rstrip())
    with _lock:
        _lines.append(entry)
        _purge_old()
    _append_persistent(entry)
    _notify()


def info(source: str, message: str) -> None:
    debug(source, message, level="info")


def warn(source: str, message: str) -> None:
    debug(source, message, level="warn")


def error(source: str, message: str) -> None:
    debug(source, message, level="error")


def get_entries() -> list[DebugLogEntry]:
    with _lock:
        _purge_old()
        return list(_lines)


def get_persistent_text() -> str:
    return "\n".join(entry.formatted for entry in _load_persistent_entries())


def get_text() -> str:
    in_memory = get_entries()
    if in_memory:
        return "\n".join(entry.formatted for entry in in_memory)
    return get_persistent_text()


def clear() -> None:
    with _lock:
        _lines.clear()
    _rewrite_persistent([])
    _notify()
