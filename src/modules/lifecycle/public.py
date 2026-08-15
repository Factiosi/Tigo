"""Application lifecycle: autostart, tray, startup behavior."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from src.core.debug_log import debug


AUTOSTART_TASK_NAME = "Tigo Autostart"


def is_runtime_available() -> bool:
    from src.core.paths import is_packaged_app

    return is_packaged_app()


def packaged_executable() -> Path | None:
    from src.core.paths import packaged_app_executable

    return packaged_app_executable()


def apply_autostart_setting(enabled: bool) -> tuple[bool, str]:
    if not is_runtime_available():
        debug("lifecycle", f"autostart={enabled} (saved; active after build)")
        return True, ""
    exe = packaged_executable()
    if exe is None:
        return False, "Не удалось определить путь к приложению."
    if enabled:
        cmd = [
            "schtasks",
            "/Create",
            "/TN",
            AUTOSTART_TASK_NAME,
            "/TR",
            f'"{exe}" --daemon',
            "/SC",
            "ONLOGON",
            "/RL",
            "HIGHEST",
            "/F",
        ]
    else:
        cmd = ["schtasks", "/Delete", "/TN", AUTOSTART_TASK_NAME, "/F"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        return False, str(exc)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return False, detail or "Не удалось изменить автозапуск."
    debug("lifecycle", f"autostart set to {enabled}")
    return True, ""


def should_start_hidden(argv: list[str] | None = None) -> bool:
    args = argv if argv is not None else sys.argv
    if "--tray" in args:
        return True
    if "--ui" in args:
        return False
    if not is_runtime_available():
        return False
    from src.core.settings import get_settings

    return get_settings().start_minimized_to_tray


def ensure_daemon_running(*, timeout: float = 15.0) -> tuple[bool, str, bool]:
    from src.daemon.ipc import is_daemon_running
    from src.daemon.ui_launcher import launch_daemon

    if is_daemon_running():
        return True, "", False

    ok, msg = launch_daemon()
    if not ok:
        return False, msg, False

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_daemon_running():
            debug("lifecycle", "daemon is ready")
            return True, "", True
        time.sleep(0.1)

    return False, "Фоновый процесс не ответил. Запустите: python run.py --daemon", True


def require_daemon_for_gui() -> None:
    """GUI cannot run without the background daemon."""
    ok, msg, _spawned = ensure_daemon_running()
    if ok:
        return
    from src.core.paths import APP_NAME

    text = msg or "Не удалось запустить фоновый процесс Tigo."
    if is_runtime_available() and "WinError 2" in text:
        text = (
            f"{text}\n\n"
            "Проверьте, что запускаете полную папку dist\\Tigo\\ "
            "(Tigo.exe + flet_client\\ + icons\\)."
        )
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, 0x10)
    except OSError:
        pass
    print(text, file=sys.stderr)
    raise SystemExit(1)


def handle_window_close(page, close_action: str) -> bool:
    """Return True if close was handled (minimize to daemon), False to exit."""
    if close_action != "minimize_tray":
        return False
    ok, msg, _spawned = ensure_daemon_running()
    if not ok:
        debug("lifecycle", f"daemon start failed: {msg}", level="error")
        return False
    debug("lifecycle", "GUI closing; daemon keeps winws running")
    return True


def launch_last_strategy_if_configured(*, from_daemon: bool = False) -> None:
    from src.core.settings import get_settings
    from src.daemon.ipc import is_daemon_running
    from src.kernel.public import get_runtime_status, start_custom_strategy, start_strategy
    from src.modules.strategies.repository import list_strategies

    if not from_daemon and is_daemon_running():
        return

    settings = get_settings()
    if not settings.launch_last_strategy_on_startup:
        return
    if get_runtime_status().running:
        return
    if settings.strategy_source == "custom":
        if settings.custom_strategy_args.strip():
            start_custom_strategy(settings.custom_strategy_args)
        return
    if settings.selected_strategy:
        for strategy in list_strategies():
            if strategy.id == settings.selected_strategy:
                start_strategy(strategy)
                return
