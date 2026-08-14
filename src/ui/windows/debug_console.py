"""Launch the debug console in a separate process."""

from __future__ import annotations

import subprocess
import sys

from src.core.debug_log import info
from src.core.paths import program_root

_process: subprocess.Popen[bytes] | None = None


def _launch_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--debug-console"]
    script = program_root() / "debug_console_app.py"
    return [sys.executable, str(script)]


def open_debug_console() -> tuple[bool, str]:
    """Spawn a standalone Flet window. Returns (ok, message)."""
    global _process

    if _process is not None and _process.poll() is not None:
        _process = None

    if _process is not None and _process.poll() is None:
        return True, "Консоль отладки уже открыта."

    if not getattr(sys, "frozen", False):
        script = program_root() / "debug_console_app.py"
        if not script.exists():
            return False, f"Не найден файл: {script}"

    try:
        _process = subprocess.Popen(
            _launch_command(),
            cwd=str(program_root()),
        )
    except OSError as exc:
        return False, f"Не удалось открыть консоль: {exc}"

    info("debug_console", "debug console subprocess started")
    return True, "Консоль отладки открыта."
