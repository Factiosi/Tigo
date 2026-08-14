"""Parse and render strategy test log lines."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable

from src.theme import T

NAME_COL_MIN = 24
TOKEN_COL_WIDTHS = (10, 11, 11)


class TestLogLevel(str, Enum):
    INFO = "info"
    OK = "ok"
    WARN = "warn"
    ERROR = "error"


@dataclass(frozen=True)
class TestLogLine:
    timestamp: str
    text: str
    level: TestLogLevel


@dataclass(frozen=True)
class ParsedTestRow:
    name: str
    tokens: tuple[str, ...]
    ping: str | None


@dataclass(frozen=True)
class TableLayout:
    name_width: int
    token_widths: tuple[int, ...]


_listeners: list[Callable[[], None]] = []
_lines: list[TestLogLine] = []
_MAX_LINES = 800

_TEST_ROW_PIPE = re.compile(
    r"^(?P<name>\S+)\s+(?:(?P<tokens>(?:\S+\s+)+)\|\s*Ping:\s*(?P<ping>.+)|:\s*\|\s*Ping:\s*(?P<ping_empty>.+))$"
)
_TEST_ROW_PING_ONLY = re.compile(r"^(?P<name>\S+)\s+Ping:\s*(?P<ping>.+)$")


def line_color(level: TestLogLevel) -> str:
    if level == TestLogLevel.OK:
        return T.STATUS_ACTIVE
    if level == TestLogLevel.WARN:
        return T.STATUS_EXPIRING
    if level == TestLogLevel.ERROR:
        return T.STATUS_ERROR
    return T.TEXT


def token_color(token: str) -> str:
    upper = token.upper()
    if "ERROR" in upper or "SSL" in upper or "FAIL" in upper:
        return T.STATUS_ERROR
    if "UNSUP" in upper:
        return T.STATUS_EXPIRING
    if ":OK" in upper or upper.endswith("OK"):
        return T.STATUS_ACTIVE
    return T.TEXT


def _timestamp() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def subscribe(listener: Callable[[], None]) -> None:
    _listeners.append(listener)


def unsubscribe(listener: Callable[[], None]) -> None:
    if listener in _listeners:
        _listeners.remove(listener)


def _notify() -> None:
    for listener in list(_listeners):
        listener()


def parse_test_row(text: str) -> ParsedTestRow | None:
    stripped = text.strip()
    match = _TEST_ROW_PIPE.match(stripped)
    if match:
        ping = match.group("ping") or match.group("ping_empty")
        tokens_raw = match.group("tokens") or ""
        tokens = tuple(part for part in tokens_raw.split() if part)
        return ParsedTestRow(match.group("name"), tokens, (ping or "").strip())
    match = _TEST_ROW_PING_ONLY.match(stripped)
    if match:
        return ParsedTestRow(match.group("name"), (), match.group("ping").strip())
    return None


def compute_table_layout(lines: list[TestLogLine]) -> TableLayout:
    parsed = [parse_test_row(line.text) for line in lines]
    names = [row.name for row in parsed if row]
    name_width = max([len(name) for name in names] + [NAME_COL_MIN])
    max_tokens = max([len(row.tokens) for row in parsed if row], default=0)
    token_widths = TOKEN_COL_WIDTHS
    if max_tokens > len(token_widths):
        token_widths = token_widths + (11,) * (max_tokens - len(token_widths))
    return TableLayout(name_width=name_width, token_widths=token_widths)


def _classify_console_line(text: str) -> TestLogLevel:
    upper = text.upper()
    row = parse_test_row(text)
    if row and row.tokens:
        if any(token_color(token) == T.STATUS_ERROR for token in row.tokens):
            return TestLogLevel.ERROR
        if any(token_color(token) == T.STATUS_EXPIRING for token in row.tokens):
            return TestLogLevel.WARN
        return TestLogLevel.OK
    if row and row.ping:
        if row.ping.lower() in {"timeout", "n/a"}:
            return TestLogLevel.WARN
        return TestLogLevel.OK
    if "[ERROR]" in upper or " ОШИБКА" in upper or upper.startswith("FAIL"):
        return TestLogLevel.ERROR
    if "[WARN" in upper or "WARNING" in upper:
        return TestLogLevel.WARN
    if (
        "[OK]" in upper
        or "ALL TESTS FINISHED" in upper
        or "BEST STRATEGY" in upper
        or "BEST CONFIG" in upper
        or "RESULTS SAVED" in upper
        or ": FULL" in upper
        or ": PARTIAL" in upper
        or ": FAILED" in upper
    ):
        return TestLogLevel.OK
    return TestLogLevel.INFO


def append(text: str, *, level: TestLogLevel = TestLogLevel.INFO) -> None:
    line = TestLogLine(_timestamp(), text.rstrip(), level)
    _lines.append(line)
    if len(_lines) > _MAX_LINES:
        del _lines[: len(_lines) - _MAX_LINES]
    _notify()


def append_from_console(text: str) -> None:
    stripped = text.strip()
    if not stripped:
        return
    append(stripped, level=_classify_console_line(stripped))


def get_lines() -> list[TestLogLine]:
    return list(_lines)


def clear() -> None:
    _lines.clear()
    _notify()


def _span_parts(full: str, parts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Build contiguous (text, color) chunks from ordered labeled parts."""
    return parts


def line_text_spans(
    line: TestLogLine,
    *,
    layout: TableLayout | None = None,
) -> list[tuple[str, str]]:
    """Return (text, color) segments for one journal line."""
    layout = layout or TableLayout(name_width=NAME_COL_MIN, token_widths=TOKEN_COL_WIDTHS)
    prefix = f"[{line.timestamp}] "
    segments: list[tuple[str, str]] = [(prefix, T.TEXT_MUTED)]

    row = parse_test_row(line.text)
    if not row:
        segments.append((line.text, line_color(line.level)))
        return segments

    body_parts: list[tuple[str, str]] = []
    body_parts.append((row.name.ljust(layout.name_width), T.TEXT))

    if row.tokens:
        body_parts.append(("    ", T.TEXT))
        token_widths = layout.token_widths
        for index, token in enumerate(row.tokens):
            width = token_widths[index] if index < len(token_widths) else 11
            body_parts.append((" ", T.TEXT))
            body_parts.append((token.ljust(width), token_color(token)))
        ping_color = (
            T.STATUS_EXPIRING
            if row.ping and row.ping.lower() in {"timeout", "n/a"}
            else T.STATUS_ACTIVE
        )
        body_parts.append(("  | Ping: ", T.TEXT_MUTED))
        body_parts.append((row.ping or "", ping_color))
    else:
        ping_color = T.STATUS_EXPIRING if row.ping and row.ping.lower() in {"timeout", "n/a"} else T.STATUS_ACTIVE
        body_parts.append(("   Ping: ", T.TEXT_MUTED))
        body_parts.append((row.ping or "", ping_color))

    segments.extend(body_parts)
    return segments
