r"""Запуск TigoUpdate: окно обновления, которое само скачивает и ставит новую версию.

Установка кладёт TigoUpdate в Program Files\Tigo\updater. Запускать его оттуда нельзя: установщик
закрывает всё, что держит файлы Program Files\Tigo. Поэтому Tigo один раз копирует папку в
%LOCALAPPDATA%\Tigo\updater\<ревизия> и запускает копию. Новая ревизия ложится рядом и не
трогает работающую.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from src.core.debug_log import debug
from src.core.paths import APP_NAME, is_packaged_app, program_root, temp_dir
from src.modules.updates.splash_status import clear_update_status, status_path, write_update_status

# Растёт при каждом изменении TigoUpdate, иначе Tigo продолжит запускать старую копию.
UPDATER_REVISION = 2
_EXE = "TigoUpdate.exe"


def bundled_updater_dir() -> Path:
    return program_root() / "updater"


def updater_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / APP_NAME / "updater"


def ensure_updater() -> Path | None:
    """Путь к копии TigoUpdate.exe вне Program Files; копирует при первом запуске ревизии."""
    target = updater_root() / str(UPDATER_REVISION)
    if (target / _EXE).is_file():
        return target / _EXE
    source = bundled_updater_dir()
    if not (source / _EXE).is_file():
        debug("app_updates", f"{_EXE} is missing in {source}", level="error")
        return None
    staging = target.with_name(target.name + ".tmp")
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(source, staging)
    shutil.rmtree(target, ignore_errors=True)
    staging.rename(target)
    for old in updater_root().iterdir():
        if old != target:
            shutil.rmtree(old, ignore_errors=True)
    return target / _EXE


def launch_updater(*, version: str, from_version: str, installer_url: str, checksum_url: str) -> bool:
    """Отдать обновление TigoUpdate. False — окно не запустилось, Tigo ставит обновление сам."""
    if sys.platform != "win32" or not is_packaged_app():
        return False
    try:
        exe = ensure_updater()
    except OSError as exc:
        debug("app_updates", f"failed to install {_EXE}: {exc}", level="error")
        return False
    if exe is None:
        return False
    clear_update_status()
    args = [
        str(exe),
        "--version", version,
        "--from", from_version,
        "--installer-url", installer_url,
        "--checksum-url", checksum_url,
        "--work-dir", str(temp_dir() / "app-update"),
        "--done-file", str(status_path()),
    ]
    try:
        subprocess.Popen(
            args,
            cwd=str(exe.parent),
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            close_fds=True,
        )
    except OSError as exc:
        debug("app_updates", f"failed to launch {_EXE}: {exc}", level="error")
        return False
    return True


def signal_update_splash_done(message: str = "Обновление завершено.") -> None:
    write_update_status("done", message)
