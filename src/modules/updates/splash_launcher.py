"""Launch the standalone TigoUpdate.exe progress window."""

from __future__ import annotations

import shutil
import subprocess
import sys

from src.core.debug_log import debug
from src.core.paths import app_data_root, is_packaged_app, program_root
from src.modules.updates.splash_status import write_update_status

_SPLASH_NAME = "TigoUpdate.exe"


def update_splash_install_path():
    return app_data_root() / _SPLASH_NAME


def bundled_update_splash_path():
    return program_root() / _SPLASH_NAME


def ensure_update_splash_exe():
    if not is_packaged_app():
        return None
    bundled = bundled_update_splash_path()
    if not bundled.is_file():
        debug("app_updates", "bundled TigoUpdate.exe is missing", level="error")
        return None
    dest = update_splash_install_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not dest.exists() or bundled.stat().st_mtime_ns > dest.stat().st_mtime_ns:
            shutil.copy2(bundled, dest)
    except OSError as exc:
        debug("app_updates", f"failed to install TigoUpdate.exe: {exc}", level="error")
        return bundled if bundled.is_file() else None
    return dest


def launch_update_splash(*, target_version: str = "") -> bool:
    if sys.platform != "win32":
        return False
    exe = ensure_update_splash_exe()
    if exe is None:
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
