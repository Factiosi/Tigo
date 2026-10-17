"""Winws launch specification types and argv tokenization."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WinwsLaunchSpec:
    exe: Path
    argv: list[str]
    cwd: Path
    strategy_name: str
    strategy_id: str


def tokenize_winws_args(args: str) -> list[str]:
    tokens = shlex.split(args, posix=False)
    return [_normalize_winws_argv_token(token) for token in tokens]


def _normalize_winws_argv_token(token: str) -> str:
    """Strip cmd-style quotes from argv tokens for CreateProcess."""
    text = token.strip()
    if text.startswith("--") and "=" in text:
        key, _, value = text.partition("=")
        return f"{key}={_strip_outer_quotes(value)}"
    return _strip_outer_quotes(text)


def _strip_outer_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return text[1:-1]
    return text
