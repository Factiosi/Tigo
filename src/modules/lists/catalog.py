"""Flowseal list file catalog."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.core.paths import USER_LIST_FILES, VERSIONED_LIST_FILES, flowseal_user_lists_dir, flowseal_version_lists_dir
from src.core.settings import get_settings


class ListKind(str, Enum):
    USER = "user"
    VERSIONED = "versioned"


@dataclass(frozen=True)
class ListEntry:
    name: str
    path: Path
    kind: ListKind


def list_user_entries() -> list[ListEntry]:
    root = flowseal_user_lists_dir()
    return [
        ListEntry(name=name, path=root / name, kind=ListKind.USER)
        for name in USER_LIST_FILES
    ]


def list_versioned_entries(version: str | None = None) -> list[ListEntry]:
    settings = get_settings()
    ver = version or settings.active_version
    if not ver:
        return []
    root = flowseal_version_lists_dir(ver)
    entries: list[ListEntry] = []
    for name in VERSIONED_LIST_FILES:
        path = root / name
        if path.exists():
            entries.append(ListEntry(name=name, path=path, kind=ListKind.VERSIONED))
    if not entries and root.exists():
        for path in sorted(root.glob("*.txt")):
            if path.name not in USER_LIST_FILES:
                entries.append(ListEntry(name=path.name, path=path, kind=ListKind.VERSIONED))
    return entries
