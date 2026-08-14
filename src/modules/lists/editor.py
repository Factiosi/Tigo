"""Open list files in the system default editor."""

from __future__ import annotations

import os
from pathlib import Path

from src.core.debug_log import debug


def open_in_default_editor(path: Path) -> tuple[bool, str]:
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
        debug("lists", f"opened {path}")
        return True, f"Открыт: {path.name}"
    except OSError as exc:
        return False, str(exc)
