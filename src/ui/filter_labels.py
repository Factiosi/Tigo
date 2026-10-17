"""Human-readable labels for runtime filter modes."""

from __future__ import annotations

from src.core.settings import GameFilterMode, IpsetFilterMode

GAME_FILTER_OPTIONS: list[tuple[GameFilterMode, str]] = [
    ("off", "Выключен"),
    ("all", "TCP и UDP"),
    ("tcp", "Только TCP"),
    ("udp", "Только UDP"),
]

IPSET_FILTER_OPTIONS: list[tuple[IpsetFilterMode, str]] = [
    ("none", "Отключён"),
    ("loaded", "Из листа"),
    ("any", "Все IP"),
]

_GAME_LABELS = dict(GAME_FILTER_OPTIONS)
_IPSET_LABELS = dict(IPSET_FILTER_OPTIONS)


def game_filter_label(mode: str) -> str:
    return _GAME_LABELS.get(mode, mode)  # type: ignore[arg-type]


def ipset_filter_label(mode: str) -> str:
    return _IPSET_LABELS.get(mode, mode)  # type: ignore[arg-type]
