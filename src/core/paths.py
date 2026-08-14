"""Application path layout.

Runtime (winws, utils) lives next to the installed program.
Flowseal strategies, versioned lists, user lists and fake bins live under AppData.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

APP_NAME = "Tigo"
LEGACY_APP_DATA_NAMES = ("Z1UI",)
SERVICE_NAME = "zapret"
REGISTRY_STRATEGY_VALUE = "zapret-discord-youtube"

USER_LIST_FILES = (
    "list-general-user.txt",
    "list-exclude-user.txt",
    "ipset-exclude-user.txt",
)

VERSIONED_LIST_FILES = (
    "list-general.txt",
    "list-exclude.txt",
    "list-google.txt",
    "ipset-all.txt",
    "ipset-exclude.txt",
)

GITHUB_REPO = "Flowseal/zapret-discord-youtube"
GITHUB_VERSION_URL = (
    "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/main/.service/version.txt"
)
GITHUB_RELEASE_API = (
    "https://api.github.com/repos/Flowseal/zapret-discord-youtube/releases/latest"
)
GITHUB_RELEASE_PAGE = "https://github.com/Flowseal/zapret-discord-youtube/releases/latest"


def program_root() -> Path:
    """Install directory (``Program Files\\Tigo`` when packaged, repo root in dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resources_dir() -> Path:
    return program_root() / "resources"


def runtime_version_path() -> Path:
    return program_root() / "runtime-version.txt"


def bin_dir() -> Path:
    """winws.exe and WinDivert drivers."""
    return program_root() / "bin"


def utils_dir() -> Path:
    return program_root() / "utils"


def default_app_data_root() -> Path:
    base = os.environ.get("APPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_NAME


def bootstrap_settings_path() -> Path:
    """Fixed bootstrap settings file — never moves with storage_root."""
    return default_app_data_root() / "settings.json"


def app_data_root() -> Path:
    try:
        from src.core.settings import get_settings

        settings = get_settings()
        if settings.storage_root:
            return Path(settings.storage_root)
    except Exception:  # noqa: BLE001
        pass
    return default_app_data_root()


def normalize_storage_path(raw: str) -> Path:
    text = raw.strip().strip('"')
    if not text:
        raise ValueError("Укажите путь.")
    path = Path(text).expanduser().resolve()
    if path.name.lower() != APP_NAME.lower():
        path = path / APP_NAME
    return path


def settings_path() -> Path:
    return bootstrap_settings_path()


def debug_log_path() -> Path:
    return app_data_root() / "debug.log"


def cache_dir() -> Path:
    return app_data_root() / "cache"


def test_results_cache_path() -> Path:
    return cache_dir() / "test_results.json"


def strategies_root() -> Path:
    return app_data_root() / "strategies"


def flowseal_root() -> Path:
    return strategies_root() / "flowseal"


def flowseal_version_dir(version: str) -> Path:
    return flowseal_root() / version


def flowseal_version_lists_dir(version: str) -> Path:
    return flowseal_version_dir(version) / "lists"


def flowseal_user_lists_dir() -> Path:
    return flowseal_root() / "user_lists"


def flowseal_fake_bin_dir() -> Path:
    return flowseal_root() / "bin"


def staging_dir() -> Path:
    return strategies_root() / "staging"


def temp_dir() -> Path:
    path = app_data_root() / "temp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def manual_strategies_dir() -> Path:
    return strategies_root() / "manual"


# Legacy aliases (pre-flowseal layout)
def versions_dir() -> Path:
    return strategies_root() / "versions"


def version_dir(version: str) -> Path:
    return flowseal_version_dir(version)


def version_strategies_dir(version: str) -> Path:
    return flowseal_version_dir(version)


def user_lists_dir() -> Path:
    return flowseal_user_lists_dir()


def lists_dir() -> Path:
    """Deprecated global lists dir — use flowseal_version_lists_dir(active_version)."""
    return program_root() / "lists"


def custom_lists_dir() -> Path:
    return app_data_root() / "custom" / "lists"


def custom_bin_dir() -> Path:
    return app_data_root() / "custom" / "bin"


def version_bin_dir(_version: str | None = None) -> Path:
    return flowseal_fake_bin_dir()


def version_lists_dir(version: str | None = None) -> Path:
    if version:
        return flowseal_version_lists_dir(version)
    return lists_dir()


def version_utils_dir(_version: str | None = None) -> Path:
    return utils_dir()


def runtime_installed() -> bool:
    return (bin_dir() / "winws.exe").exists()


def _merge_copytree(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            if target.exists():
                _merge_copytree(item, target)
            else:
                shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def _copy_runtime_tree(source_root: Path) -> None:
    program_root().mkdir(parents=True, exist_ok=True)
    src_bin = source_root / "bin"
    if src_bin.exists():
        dest_bin = bin_dir()
        dest_bin.mkdir(parents=True, exist_ok=True)
        for item in src_bin.iterdir():
            if item.suffix.lower() == ".bin":
                continue
            target = dest_bin / item.name
            if item.is_dir():
                if target.exists():
                    _merge_copytree(item, target)
                else:
                    shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
    src_utils = source_root / "utils"
    if src_utils.exists():
        dest_utils = utils_dir()
        if dest_utils.exists():
            _merge_copytree(src_utils, dest_utils)
        else:
            shutil.copytree(src_utils, dest_utils)


def _migrate_old_versions_to_flowseal() -> None:
    old_versions = strategies_root() / "versions"
    if not old_versions.exists():
        return
    flowseal_root().mkdir(parents=True, exist_ok=True)
    for entry in old_versions.iterdir():
        if not entry.is_dir():
            continue
        dest = flowseal_version_dir(entry.name)
        if dest.exists():
            continue
        old_strategies = entry / "strategies"
        if old_strategies.exists():
            dest.mkdir(parents=True, exist_ok=True)
            for txt in old_strategies.glob("*.txt"):
                shutil.copy2(txt, dest / txt.name)
            meta_src = entry / "meta.json"
            if meta_src.exists():
                shutil.copy2(meta_src, dest / "meta.json")
        else:
            shutil.copytree(entry, dest, dirs_exist_ok=True)


def _migrate_user_lists() -> None:
    old = app_data_root() / "user-lists"
    new = flowseal_user_lists_dir()
    new.mkdir(parents=True, exist_ok=True)
    if not old.exists():
        return
    for name in USER_LIST_FILES:
        src = old / name
        dest = new / name
        if src.exists() and not dest.exists():
            shutil.copy2(src, dest)


def _migrate_global_lists_and_bins(active_version: str | None) -> None:
    """Move legacy program_root lists and fake bins into flowseal layout."""
    flowseal_fake_bin_dir().mkdir(parents=True, exist_ok=True)
    legacy_bin = bin_dir()
    if legacy_bin.exists():
        for item in legacy_bin.glob("*.bin"):
            target = flowseal_fake_bin_dir() / item.name
            if not target.exists():
                shutil.copy2(item, target)

    legacy_lists = program_root() / "lists"
    if not legacy_lists.exists():
        return
    ver = active_version
    if not ver:
        candidates = sorted(
            (p.name for p in flowseal_root().iterdir() if p.is_dir() and p.name != "bin"),
            reverse=True,
        )
        ver = candidates[0] if candidates else None
    if not ver:
        return
    dest_lists = flowseal_version_lists_dir(ver)
    dest_lists.mkdir(parents=True, exist_ok=True)
    for item in legacy_lists.iterdir():
        if item.name in USER_LIST_FILES:
            continue
        target = dest_lists / item.name
        if item.is_file() and not target.exists():
            shutil.copy2(item, target)


def migrate_to_flowseal_layout() -> None:
    active_version: str | None = None
    path = settings_path()
    if path.exists():
        try:
            active_version = json.loads(path.read_text(encoding="utf-8")).get("active_version")
        except (json.JSONDecodeError, OSError):
            active_version = None
    _migrate_old_versions_to_flowseal()
    _migrate_user_lists()
    _migrate_global_lists_and_bins(active_version)


def migrate_legacy_layout() -> None:
    """Move winws runtime from old Roaming ``versions/<ver>/`` into program root."""
    if runtime_installed():
        return
    old_versions = strategies_root() / "versions"
    if not old_versions.exists():
        return

    active_version: str | None = None
    path = settings_path()
    if path.exists():
        try:
            active_version = json.loads(path.read_text(encoding="utf-8")).get("active_version")
        except (json.JSONDecodeError, OSError):
            active_version = None

    candidates: list[Path] = []
    if active_version:
        candidates.append(old_versions / active_version)
    candidates.extend(sorted(old_versions.iterdir(), reverse=True))

    seen: set[Path] = set()
    for entry in candidates:
        if not entry.is_dir() or entry in seen:
            continue
        seen.add(entry)
        if (entry / "bin" / "winws.exe").exists():
            _copy_runtime_tree(entry)
            runtime_version_path().write_text(entry.name + "\n", encoding="utf-8")
            return


def _migrate_legacy_app_data() -> None:
    """Copy Roaming data from pre-rename folders (e.g. Z1UI → Tigo)."""
    new_root = default_app_data_root()
    if new_root.exists() and any(new_root.iterdir()):
        return
    base = os.environ.get("APPDATA")
    if not base:
        return
    roaming = Path(base)
    for legacy_name in LEGACY_APP_DATA_NAMES:
        if legacy_name == APP_NAME:
            continue
        old_root = roaming / legacy_name
        if not old_root.exists():
            continue
        new_root.mkdir(parents=True, exist_ok=True)
        for item in old_root.iterdir():
            dest = new_root / item.name
            if dest.exists():
                continue
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        return


def ensure_layout() -> None:
    _migrate_legacy_app_data()
    root = app_data_root()
    for path in (
        root,
        cache_dir(),
        flowseal_root(),
        flowseal_user_lists_dir(),
        flowseal_fake_bin_dir(),
        custom_lists_dir(),
        custom_bin_dir(),
        staging_dir(),
        temp_dir(),
        manual_strategies_dir(),
    ):
        path.mkdir(parents=True, exist_ok=True)

    program_root().mkdir(parents=True, exist_ok=True)
    migrate_legacy_layout()
    migrate_to_flowseal_layout()

    bin_dir().mkdir(parents=True, exist_ok=True)
    utils_dir().mkdir(parents=True, exist_ok=True)
