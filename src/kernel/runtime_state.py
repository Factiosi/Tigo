"""In-memory zapret runtime status (snapshot-first for UI)."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class RuntimePhase(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass(frozen=True)
class RuntimeStatus:
    phase: RuntimePhase
    running: bool
    strategy_name: str | None
    pid: int | None
    windivert_sys_present: bool
    error: str | None = None
    tests_running: bool = False


_lock = threading.RLock()
_phase = RuntimePhase.IDLE
_strategy_name: str | None = None
_pid: int | None = None
_error: str | None = None
_windivert_sys_present = False
_tests_running = False
_listeners: list[Callable[[], None]] = []


def subscribe(listener: Callable[[], None]) -> None:
    _listeners.append(listener)


def unsubscribe(listener: Callable[[], None]) -> None:
    if listener in _listeners:
        _listeners.remove(listener)


def _notify() -> None:
    for listener in list(_listeners):
        try:
            listener()
        except Exception:
            pass


def set_windivert_present(value: bool) -> None:
    global _windivert_sys_present
    with _lock:
        _windivert_sys_present = value
    _notify()


def set_tests_running(value: bool) -> None:
    global _tests_running
    with _lock:
        _tests_running = value
    _notify()


def mark_starting(strategy_name: str) -> None:
    global _phase, _strategy_name, _pid, _error
    with _lock:
        _phase = RuntimePhase.STARTING
        _strategy_name = strategy_name
        _pid = None
        _error = None
    _notify()


def mark_running(strategy_name: str, pid: int) -> None:
    global _phase, _strategy_name, _pid, _error
    with _lock:
        _phase = RuntimePhase.RUNNING
        _strategy_name = strategy_name
        _pid = pid
        _error = None
    _notify()


def mark_stopping() -> None:
    global _phase
    with _lock:
        _phase = RuntimePhase.STOPPING
    _notify()


def mark_stopped() -> None:
    global _phase, _strategy_name, _pid, _error
    with _lock:
        _phase = RuntimePhase.IDLE
        _strategy_name = None
        _pid = None
        _error = None
    _notify()


def mark_failed(error: str, *, strategy_name: str | None = None) -> None:
    global _phase, _strategy_name, _pid, _error
    with _lock:
        _phase = RuntimePhase.FAILED
        if strategy_name is not None:
            _strategy_name = strategy_name
        _pid = None
        _error = error
    _notify()


def sync_probe(running: bool, pid: int | None, *, strategy_name: str | None = None) -> None:
    """Update from background process monitor without clobbering starting/stopping."""
    global _phase, _pid, _strategy_name
    with _lock:
        if _tests_running and _phase == RuntimePhase.IDLE:
            return
        if _phase in {RuntimePhase.STARTING, RuntimePhase.STOPPING}:
            return
        if running:
            _phase = RuntimePhase.RUNNING
            _pid = pid
            if strategy_name:
                _strategy_name = strategy_name
        elif _phase == RuntimePhase.RUNNING:
            _phase = RuntimePhase.IDLE
            _pid = None
            _strategy_name = None
    _notify()


def get_status() -> RuntimeStatus:
    with _lock:
        running = _phase == RuntimePhase.RUNNING
        return RuntimeStatus(
            phase=_phase,
            running=running,
            strategy_name=_strategy_name,
            pid=_pid,
            windivert_sys_present=_windivert_sys_present,
            error=_error,
            tests_running=_tests_running,
        )
