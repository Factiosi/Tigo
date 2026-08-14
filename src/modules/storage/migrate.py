"""Migrate roaming data to a new storage root."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.core.debug_log import debug, info
from src.core.paths import app_data_root, default_app_data_root, ensure_layout, normalize_storage_path
from src.core.settings import get_settings, reload_settings, save_settings

_MIGRATE_NAMES = ("strategies", "custom", "cache", "debug.log")


def current_storage_display() -> str:
    return str(app_data_root())


def apply_storage_root(raw_path: str) -> tuple[bool, str]:
    try:
        new_root = normalize_storage_path(raw_path)
    except ValueError as exc:
        return False, str(exc)

    old_root = app_data_root()
    if new_root.resolve() == old_root.resolve():
        settings = get_settings()
        settings.storage_root = str(new_root)
        save_settings(settings)
        ensure_layout()
        return True, "Путь сохранён."

    new_root.mkdir(parents=True, exist_ok=True)
    if old_root.exists() and old_root.resolve() != new_root.resolve():
        for name in _MIGRATE_NAMES:
            src = old_root / name
            if not src.exists():
                continue
            dest = new_root / name
            if src.is_dir():
                if dest.exists():
                    _merge_copytree(src, dest)
                else:
                    shutil.copytree(src, dest)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(src, dest)

    settings = get_settings()
    settings.storage_root = str(new_root)
    save_settings(settings)
    reload_settings()
    ensure_layout()
    info("storage", f"migrated data {old_root} -> {new_root}")
    debug("storage", f"storage_root applied: {new_root}")
    return True, "Данные перенесены. Перезапустите приложение."


def _merge_copytree(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            if target.exists():
                _merge_copytree(item, target)
            else:
                shutil.copytree(item, target)
        elif not target.exists():
            shutil.copy2(item, target)


def reset_storage_to_default() -> str:
    return str(default_app_data_root())
