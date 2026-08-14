"""winws.exe process helpers."""

from __future__ import annotations

import subprocess


def is_winws_running() -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq winws.exe"],
        capture_output=True,
        text=True,
        encoding="cp866",
        errors="replace",
        check=False,
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
    )
    return result.returncode == 0
