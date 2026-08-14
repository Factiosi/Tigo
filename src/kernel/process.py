"""winws.exe process helpers."""

from __future__ import annotations

import subprocess

CREATE_NO_WINDOW = 0x08000000


def is_winws_running() -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq winws.exe"],
        capture_output=True,
        text=True,
        encoding="cp866",
        errors="replace",
        check=False,
        creationflags=CREATE_NO_WINDOW,
    )
    return "winws.exe" in result.stdout.lower()


def kill_winws() -> bool:
    result = subprocess.run(
        ["taskkill", "/IM", "winws.exe", "/F"],
        capture_output=True,
        text=True,
        encoding="cp866",
        errors="replace",
        check=False,
        creationflags=CREATE_NO_WINDOW,
    )
    return result.returncode == 0
