"""Persistent application settings."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Literal

from src.core.paths import bootstrap_settings_path, default_app_data_root
from src.theme import PortalHue, ThemeMode

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
    auto_check_app_updates_on_startup: bool = False
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
        if data.get("version_retention") == "keep_n":
            data["version_retention"] = "keep_previous"
            data["keep_version_count"] = 2
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def save(self, path: Path | None = None) -> None:
        file_path = path or bootstrap_settings_path()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    global _settings
    if _settings is None:
        _settings = AppSettings.load()
    return _settings


def save_settings(settings: AppSettings | None = None) -> None:
    global _settings
    target = settings or get_settings()
    target.save()
    _settings = target


def reload_settings() -> AppSettings:
    global _settings
    _settings = AppSettings.load()
    return _settings


def effective_storage_root() -> Path:
    settings = get_settings()
    if settings.storage_root:
        return Path(settings.storage_root)
    return default_app_data_root()
