"""Enable TCP timestamps (service.bat :tcp_enable)."""

from __future__ import annotations

import subprocess

CREATE_NO_WINDOW = 0x08000000


def enable_tcp_timestamps() -> bool:
    check = subprocess.run(
        ["netsh", "interface", "tcp", "show", "global"],
        capture_output=True,
        text=True,
        encoding="cp866",
        errors="replace",
        check=False,
        creationflags=CREATE_NO_WINDOW,
    )
    if "timestamps" in check.stdout.lower() and "enabled" in check.stdout.lower():
        return True

    result = subprocess.run(
        ["netsh", "interface", "tcp", "set", "global", "timestamps=enabled"],
        capture_output=True,
        text=True,
        encoding="cp866",
        errors="replace",
        check=False,
        creationflags=CREATE_NO_WINDOW,
    )
    return result.returncode == 0
