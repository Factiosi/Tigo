"""Persistent application settings."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Literal

from src.core.paths import bootstrap_settings_path, default_app_data_root
from src.theme import PortalHue, ThemeMode

_write_lock = threading.RLock()

GameFilterMode = Literal["off", "all", "tcp", "udp"]
IpsetFilterMode = Literal["loaded", "none", "any"]
VersionRetention = Literal["all", "latest_only", "keep_previous"]
StrategySource = Literal["flowseal", "custom"]
CloseAction = Literal["exit", "minimize_tray"]


@dataclass
class AppSettings:
    active_version: str | None = None
    selected_strategy: str | None = None
    game_filter: GameFilterMode = "off"
    ipset_filter: IpsetFilterMode = "loaded"
    skip_list_updates: bool = False
    version_retention: VersionRetention = "keep_previous"
    keep_version_count: int = 2
    auto_check_updates_on_startup: bool = True
    auto_promote_updates: bool = True
    auto_check_app_updates_on_startup: bool = True
    auto_install_app_updates: bool = False
    theme_mode: ThemeMode = "dark"
    portal_hue: PortalHue = "blue"
    strategy_source: StrategySource = "flowseal"
    custom_strategy_args: str = ""
    autostart_enabled: bool = False
    launch_last_strategy_on_startup: bool = False
    start_minimized_to_tray: bool = False
    close_action: CloseAction = "minimize_tray"
    storage_root: str | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> "AppSettings":
        file_path = path or bootstrap_settings_path()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            return cls()
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        if not isinstance(data, dict):
            return cls()
        if data.get("version_retention") == "keep_n":
            data["version_retention"] = "keep_previous"
            data["keep_version_count"] = 2
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def save(self, path: Path | None = None) -> None:
        file_path = path or bootstrap_settings_path()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"
        tmp = file_path.with_name(
            f".{file_path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        with _write_lock:
            try:
                tmp.write_text(payload, encoding="utf-8")
                os.replace(tmp, file_path)
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass


_settings: AppSettings | None = None
_settings_snapshot: AppSettings | None = None


def _snapshot(settings: AppSettings) -> AppSettings:
    return AppSettings(**{field.name: getattr(settings, field.name) for field in fields(AppSettings)})


def _set_settings_cache(settings: AppSettings) -> AppSettings:
    global _settings, _settings_snapshot
    _settings = settings
    _settings_snapshot = _snapshot(settings)
    return settings


def get_settings() -> AppSettings:
    global _settings
    if _settings is None:
        _set_settings_cache(AppSettings.load())
    return _settings


def save_settings(settings: AppSettings | None = None) -> None:
    disk = AppSettings.load()
    source = settings or get_settings()
    snapshot = _settings_snapshot or _snapshot(disk)
    for field in fields(AppSettings):
        incoming = getattr(source, field.name)
        baseline = getattr(snapshot, field.name)
        if incoming != baseline:
            setattr(disk, field.name, incoming)
    disk.save()
    _set_settings_cache(disk)


def reload_settings() -> AppSettings:
    return _set_settings_cache(AppSettings.load())


def effective_storage_root() -> Path:
    settings = get_settings()
    if settings.storage_root:
        return Path(settings.storage_root)
    return default_app_data_root()
