"""Spawn Tigo GUI process and track instances for shutdown."""

from __future__ import annotations

import os
import subprocess
import sys

from src.core.debug_log import debug
from src.core.paths import APP_NAME, frozen_subprocess_env, packaged_app_executable, program_root

_gui_pids: set[int] = set()
_gui_processes: list[subprocess.Popen] = []


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


def _spawn_args(*extra: str) -> tuple[list[str], dict]:
    root = program_root()
    cwd = str(root)
    kwargs: dict = {"cwd": cwd}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | getattr(subprocess, "DETACHED_PROCESS", 0)

    exe = packaged_app_executable()
    if exe is not None:
        kwargs["env"] = frozen_subprocess_env()
        return [str(exe), *extra], kwargs

    run_py = root / "run.py"
    if not run_py.is_file():
        raise FileNotFoundError(
            f"Не найден Tigo.exe или run.py в {root}. "
            "Запускайте приложение из полной папки dist\\Tigo\\."
        )
    return [sys.executable, str(run_py), *extra], kwargs


def launch_gui(*, hidden: bool = False) -> tuple[bool, str]:
    args = ["--ui"]
    if hidden:
        args.append("--tray")
    try:
        cmd, kwargs = _spawn_args(*args)
        proc = subprocess.Popen(cmd, **kwargs)
    except OSError as exc:
        return False, str(exc)
    except FileNotFoundError as exc:
        return False, str(exc)
    _gui_processes.append(proc)
    debug("daemon", f"GUI launched: {' '.join(cmd)} pid={proc.pid}")
    return True, "Окно открыто."


def launch_daemon() -> tuple[bool, str]:
    try:
        cmd, kwargs = _spawn_args("--daemon")
        subprocess.Popen(cmd, **kwargs)
    except OSError as exc:
        return False, str(exc)
    except FileNotFoundError as exc:
        return False, str(exc)
    debug("daemon", f"daemon process spawned: {' '.join(cmd)}")
    return True, "Фоновый процесс запущен."


def notify_spawn_error(message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
    except OSError:
        pass
