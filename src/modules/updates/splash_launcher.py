"""Launch TigoUpdate.exe from the install directory (Program Files)."""

from __future__ import annotations

import subprocess
import sys

from src.core.debug_log import debug
from src.core.paths import is_packaged_app, program_root
from src.modules.updates.splash_status import write_update_status

_SPLASH_NAME = "TigoUpdate.exe"


def bundled_update_splash_path():
    return program_root() / _SPLASH_NAME


def ensure_update_splash_exe():
    if not is_packaged_app():
        return None
    bundled = bundled_update_splash_path()
    return bundled if bundled.is_file() else None


def launch_update_splash(*, target_version: str = "") -> bool:
    if sys.platform != "win32":
        return False
    exe = ensure_update_splash_exe()
    if exe is None:
        debug("app_updates", "TigoUpdate.exe is missing next to Tigo.exe", level="error")
        return False
    write_update_status(
        "checking",
        "Подготовка к обновлению Tigo...",
        target_version=target_version,
    )
    creationflags = subprocess.CREATE_NO_WINDOW | getattr(subprocess, "DETACHED_PROCESS", 0)
    try:
        subprocess.Popen(
            [str(exe)],
            cwd=str(exe.parent),
            creationflags=creationflags,
            close_fds=True,
        )
    except OSError as exc:
        debug("app_updates", f"failed to launch TigoUpdate.exe: {exc}", level="error")
        return False
    return True


def signal_update_splash_done(message: str = "Обновление завершено.") -> None:
    write_update_status("done", message)
