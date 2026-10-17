"""Human-readable strategy names from flowseal file stems."""

from __future__ import annotations

import re

_ACRONYMS = frozenset({"TLS", "HTTP", "HTTPS", "TCP", "UDP", "DPI", "SNI", "DNS"})
_ALT_NUMBERED = re.compile(r"^ALT(\d+)$", re.IGNORECASE)
_PAREN_SUFFIX = re.compile(r"^(.+?)\s*(\(.+\))$")


def _format_token(token: str) -> str:
    if token in {"+", "-", "/", "&"}:
        return token
    upper = token.upper()
    if upper in _ACRONYMS:
        return upper
    alt_numbered = _ALT_NUMBERED.match(upper)
    if alt_numbered:
        return f"Alt {int(alt_numbered.group(1))}"
    if upper == "ALT":
        return "Alt"
    if token.isupper() or token.islower():
        return token.capitalize()
    return token


def _format_part(text: str) -> str:
    return " ".join(_format_token(part) for part in text.split())


def format_strategy_display_name(stem: str) -> str:
    """Turn ``general (FAKE TLS AUTO ALT3)`` into ``General (Fake TLS Auto Alt 3)``."""
    raw = stem.strip()
    if not raw:
        return raw

    match = _PAREN_SUFFIX.match(raw)
    if match:
        base = _format_part(match.group(1).strip())
        inner = match.group(2)[1:-1].strip()
        return f"{base} ({_format_part(inner)})"

    return _format_part(raw)
