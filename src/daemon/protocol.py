"""IPC message types for Z1UI daemon."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CommandName = Literal["ping", "status", "start", "stop", "open_ui", "shutdown", "register_gui"]


@dataclass
class DaemonStatus:
    running: bool
    phase: str
    strategy_name: str
    error: str
    pid: int | None


def status_to_dict(status: DaemonStatus) -> dict[str, Any]:
    return {
        "running": status.running,
        "phase": status.phase,
        "strategy_name": status.strategy_name,
        "error": status.error,
        "pid": status.pid,
    }


def status_from_dict(data: dict[str, Any]) -> DaemonStatus:
    return DaemonStatus(
        running=bool(data.get("running")),
        phase=str(data.get("phase") or "idle"),
        strategy_name=str(data.get("strategy_name") or ""),
        error=str(data.get("error") or ""),
        pid=data.get("pid") if isinstance(data.get("pid"), int) else None,
    )
