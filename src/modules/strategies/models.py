"""Strategy data models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.modules.strategies.names import format_strategy_display_name


class StrategySource(str, Enum):
    FLOWSEAL = "flowseal"
    MANUAL = "manual"


@dataclass(frozen=True)
class Strategy:
    id: str
    name: str
    source: StrategySource
    args_template: str
    path: Path
    version: str | None = None

    @property
    def display_name(self) -> str:
        return format_strategy_display_name(self.name)


@dataclass
class StrategyVersion:
    version: str
    path: Path
    strategy_count: int = 0
    has_winws: bool = False
