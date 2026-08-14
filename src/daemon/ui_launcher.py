"""Spawn Z1UI GUI process and track instances for shutdown."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from src.core.debug_log import debug
from src.modules.lifecycle.public import is_runtime_available, packaged_executable

_gui_pids: set[int] = set()
_gui_processes: list[subprocess.Popen] = []


def _run_py_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    run_py = root / "run.py"
    if run_py.exists():
        return run_py
    return root.parent / "run.py"


def register_gui_pid(pid: int | None = None) -> None:
    value = pid if pid is not None else os.getpid()
    if value > 0:
        _gui_pids.add(value)
        debug("daemon", f"registered GUI pid={value}")


def unregister_gui_pid(pid: int | None = None) -> None:
    value = pid if pid is not None else os.getpid()
    _gui_pids.discard(value)


def _prune_gui_processes() -> None:
    global _gui_processes
    _gui_processes = [proc for proc in _gui_processes if proc.poll() is None]


def _kill_pid(pid: int) -> None:
    if pid <= 0:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            os.kill(pid, 15)
    except OSError as exc:
        debug("daemon", f"failed to kill pid={pid}: {exc}", level="error")


def close_all_gui() -> None:
    _prune_gui_processes()
    targets = set(_gui_pids)
    for proc in _gui_processes:
        if proc.poll() is None:
            targets.add(proc.pid)
    for pid in targets:
        _kill_pid(pid)
    _gui_processes.clear()
    _gui_pids.clear()
    debug("daemon", "all GUI processes closed")


def launch_gui(*, hidden: bool = False) -> tuple[bool, str]:
    if is_runtime_available():
        exe = packaged_executable()
        if exe is None:
            return False, "Не удалось определить путь к приложению."
        args = [str(exe), "--ui"]
        if hidden:
            args.append("--tray")
    else:
        args = [sys.executable, str(_run_py_path()), "--ui"]
        if hidden:
            args.append("--tray")

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        proc = subprocess.Popen(args, creationflags=creationflags)
    except OSError as exc:
        return False, str(exc)
    _gui_processes.append(proc)
    debug("daemon", f"GUI launched: {' '.join(args)} pid={proc.pid}")
    return True, "Окно открыто."


def launch_daemon() -> tuple[bool, str]:
    if is_runtime_available():
        exe = packaged_executable()
        if exe is None:
            return False, "Не удалось определить путь к приложению."
        args = [str(exe), "--daemon"]
    else:
        args = [sys.executable, str(_run_py_path()), "--daemon"]

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        subprocess.Popen(args, creationflags=creationflags)
    except OSError as exc:
        return False, str(exc)
    debug("daemon", "daemon process spawned")
    return True, "Фоновый процесс запущен."
