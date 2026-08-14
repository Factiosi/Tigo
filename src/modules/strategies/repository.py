"""Strategy storage and version management."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from src.core.paths import (
    USER_LIST_FILES,
    VERSIONED_LIST_FILES,
    ensure_layout,
    flowseal_root,
    flowseal_user_lists_dir,
    flowseal_version_dir,
    flowseal_version_lists_dir,
    manual_strategies_dir,
    runtime_installed,
)
from src.core.debug_log import debug
from src.core.settings import AppSettings, get_settings, save_settings
from src.modules.strategies.models import Strategy, StrategySource, StrategyVersion
from src.modules.strategies.parser import read_strategy_args

NO_FLOWSEAL_STRATEGIES_LABEL = (
    "Стратегии отсутствуют, проверьте обновления в настройках"
)


def bootstrap_user_lists(source_root: Path | None = None) -> None:
    """Create default user list files; never overwrite existing."""
    ensure_layout()
    defaults = {
        "ipset-exclude-user.txt": "203.0.113.113/32\n",
        "list-general-user.txt": (
            "# Never leave this file empty\n"
            "domain.example.abc\n"
        ),
        "list-exclude-user.txt": "domain.example.abc\n",
    }
    dest_dir = flowseal_user_lists_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name in USER_LIST_FILES:
        path = dest_dir / name
        if path.exists():
            continue
        if source_root:
            src = source_root / "lists" / name
            if src.exists():
                shutil.copy2(src, path)
                continue
        path.write_text(defaults[name], encoding="utf-8")


def list_installed_versions() -> list[StrategyVersion]:
    ensure_layout()
    result: list[StrategyVersion] = []
    root = flowseal_root()
    if not root.exists():
        return result
    for entry in sorted(root.iterdir(), reverse=True):
        if not entry.is_dir() or entry.name in ("user_lists", "bin"):
            continue
        strategies = list(entry.glob("*.txt"))
        if not strategies and not (entry / "meta.json").exists():
            continue
        result.append(
            StrategyVersion(
                version=entry.name,
                path=entry,
                strategy_count=len(strategies),
                has_winws=runtime_installed(),
            )
        )
    return result


def flowseal_version_select_options(settings: AppSettings | None = None) -> list[tuple[str, str]]:
    """Options for the flowseal version select; includes active version even if meta is missing."""
    settings = settings or get_settings()
    options: list[tuple[str, str]] = [(v.version, v.version) for v in list_installed_versions()]
    known = {key for key, _ in options}
    if settings.active_version and settings.active_version not in known:
        active_dir = flowseal_version_dir(settings.active_version)
        if active_dir.exists():
            options.insert(0, (settings.active_version, settings.active_version))
    if not options:
        return [("", "Не установлены")]
    return options


def has_flowseal_strategies(settings: AppSettings | None = None) -> bool:
    settings = settings or get_settings()
    return any(s.source == StrategySource.FLOWSEAL for s in list_strategies(settings))


def list_strategies(settings: AppSettings | None = None) -> list[Strategy]:
    settings = settings or get_settings()
    strategies: list[Strategy] = []

    if settings.active_version:
        sdir = flowseal_version_dir(settings.active_version)
        if sdir.exists():
            for path in sorted(sdir.glob("*.txt")):
                strategies.append(
                    Strategy(
                        id=f"flowseal:{path.stem}",
                        name=path.stem,
                        source=StrategySource.FLOWSEAL,
                        args_template=read_strategy_args(path),
                        path=path,
                        version=settings.active_version,
                    )
                )

    mdir = manual_strategies_dir()
    if mdir.exists():
        for path in sorted(mdir.glob("*.txt")):
            strategies.append(
                Strategy(
                    id=f"manual:{path.stem}",
                    name=path.stem,
                    source=StrategySource.MANUAL,
                    args_template=read_strategy_args(path),
                    path=path,
                )
            )
    return strategies


def get_active_version_path(settings: AppSettings | None = None) -> Path | None:
    settings = settings or get_settings()
    if not settings.active_version:
        return None
    path = flowseal_version_dir(settings.active_version)
    return path if path.exists() else None


def set_active_version(version: str) -> None:
    settings = get_settings()
    settings.active_version = version
    save_settings(settings)
    debug("strategies", f"active version set to {version}")


def write_version_meta(version: str, *, source: str = "github") -> None:
    meta = {
        "version": version,
        "source": source,
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }
    (flowseal_version_dir(version) / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _retention_keep_count(settings: AppSettings) -> int | None:
    if settings.version_retention == "all":
        return None
    if settings.version_retention == "latest_only":
        return 1
    return max(2, settings.keep_version_count)


def apply_version_retention(settings: AppSettings | None = None) -> list[str]:
    settings = settings or get_settings()
    keep = _retention_keep_count(settings)
    if keep is None:
        return []
    return _purge_versions(keep=keep, settings=settings)


def purge_stale_versions(*, keep: int = 1, settings: AppSettings | None = None) -> list[str]:
    """Force-delete all but the newest ``keep`` versions."""
    settings = settings or get_settings()
    return _purge_versions(keep=max(1, keep), settings=settings)


def _purge_versions(*, keep: int, settings: AppSettings) -> list[str]:
    installed = list_installed_versions()
    removed: list[str] = []
    for entry in installed[keep:]:
        if settings.active_version == entry.version:
            continue
        shutil.rmtree(entry.path, ignore_errors=True)
        removed.append(entry.version)
        debug("strategies", f"removed version {entry.version}")
        from src.modules.strategy_testing.results import drop_version

        drop_version(entry.version)
    return removed


def list_versioned_list_files(version: str | None = None) -> list[Path]:
    settings = get_settings()
    ver = version or settings.active_version
    if not ver:
        return []
    lists_dir = flowseal_version_lists_dir(ver)
    if not lists_dir.exists():
        return []
    known = {name for name in VERSIONED_LIST_FILES}
    return sorted(p for p in lists_dir.iterdir() if p.is_file() and p.name in known)


def import_local_package(source_root: Path, version: str) -> Path:
    """Import a local zapret-discord-youtube folder (dev / offline)."""
    from src.modules.updates.transformer import transform_package

    ensure_layout()
    bootstrap_user_lists(source_root)
    dest = transform_package(source_root, version, skip_list_updates=False)
    write_version_meta(version, source="local")
    set_active_version(version)
    return dest
