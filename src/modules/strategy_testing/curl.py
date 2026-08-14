"""Test helpers for strategy runner."""

from __future__ import annotations

import shutil


def curl_available() -> tuple[bool, str]:
    if shutil.which("curl.exe"):
        return True, ""
    return False, "Требуется curl.exe (обычно входит в Windows 10/11)."
