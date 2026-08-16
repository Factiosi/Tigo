"""One-time migration shipped only in Tigo 1.3.1."""

from __future__ import annotations

from src.core.debug_log import debug
from src.core.paths import app_data_root, is_packaged_app

_LEGACY_NAME = "TigoUpdate.exe"


def run() -> None:
    if not is_packaged_app():
        return
    legacy = app_data_root() / _LEGACY_NAME
    if not legacy.is_file():
        return
    try:
        legacy.unlink()
        debug("migration", f"removed legacy {_LEGACY_NAME} from AppData")
    except OSError as exc:
        debug("migration", f"failed to remove legacy {_LEGACY_NAME}: {exc}", level="error")
