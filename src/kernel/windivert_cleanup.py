"""WinDivert driver service cleanup."""

from __future__ import annotations

import subprocess

CREATE_NO_WINDOW = 0x08000000


def _run(args: list[str]) -> None:
    subprocess.run(
        args,
        capture_output=True,
        check=False,
        creationflags=CREATE_NO_WINDOW,
    )


def cleanup_windivert_services() -> None:
    for name in ("WinDivert", "WinDivert14"):
        _run(["net", "stop", name])
        _run(["sc", "delete", name])
