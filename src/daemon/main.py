"""Tigo background daemon entry."""

from __future__ import annotations

import signal
import sys
import threading
import time

from src.core.debug_log import info, warn
from src.core.paths import APP_NAME, ensure_layout
from src.core.settings import get_settings
from src.daemon.ipc import IpcServer, build_status_response
from src.daemon.protocol import CommandName
from src.daemon.tray import TrayController
from src.daemon.ui_launcher import close_all_gui, launch_gui, register_gui_pid
from src.kernel.process_monitor import start_monitor, stop_monitor
from src.kernel.public import get_runtime_status, initialize_runtime, start_custom_strategy, start_strategy, stop_strategy
from src.modules.lifecycle.public import launch_last_strategy_if_configured
from src.modules.strategies.repository import bootstrap_user_lists, list_strategies
from src.modules.updates.service import run_startup_updates
from src.modules.strategy_testing.results import load_cache


class TigoDaemon:
    def __init__(self) -> None:
        self._shutdown = threading.Event()
        self._tray: TrayController | None = None
        self._ipc = IpcServer(self._handle_command)
        self._bootstrap_done = threading.Event()

    def run(self) -> None:
        info("daemon", f"starting {APP_NAME} daemon")
        get_settings()
        self._ipc.start()
        info("daemon", "IPC ready")

        self._tray = TrayController(
            on_start=self._tray_start,
            on_stop=self._tray_stop,
            on_shutdown=self._request_shutdown_from_tray,
            status_provider=self._tray_status,
        )
        tray_thread = threading.Thread(target=self._tray.start, daemon=True, name="z1ui-tray")
        tray_thread.start()

        threading.Thread(target=self._bootstrap_runtime, daemon=True, name="z1ui-daemon-bootstrap").start()

        def handle_signal(_signum, _frame) -> None:
            self._request_shutdown(stop_icon=True)

        signal.signal(signal.SIGINT, handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, handle_signal)

        while not self._shutdown.is_set():
            time.sleep(0.5)
        stop_monitor()
        self._ipc.stop()
        info("daemon", "daemon stopped")

    def _bootstrap_runtime(self) -> None:
        try:
            ensure_layout()
            bootstrap_user_lists()
            load_cache()
            initialize_runtime()
            start_monitor()
            run_startup_updates(
                on_message=lambda msg, error=False: warn("updates", msg) if error else info("updates", msg)
            )
            launch_last_strategy_if_configured(from_daemon=True)
            info("daemon", "runtime bootstrap complete")
        except Exception as exc:  # noqa: BLE001
            warn("daemon", f"runtime bootstrap failed: {exc}")
        finally:
            self._bootstrap_done.set()

    def _tray_status(self) -> tuple[bool, bool]:
        status = get_runtime_status()
        busy = status.phase.value in {"starting", "stopping"}
        return status.running, busy

    def _tray_start(self) -> None:
        if not self._bootstrap_done.is_set():
            warn("daemon", "runtime still initializing")
        settings = get_settings()
        if settings.strategy_source == "custom":
            if settings.custom_strategy_args.strip():
                start_custom_strategy(settings.custom_strategy_args)
            return
        if settings.selected_strategy:
            for strategy in list_strategies():
                if strategy.id == settings.selected_strategy:
                    start_strategy(strategy)
                    return

    def _tray_stop(self) -> None:
        stop_strategy()

    def _request_shutdown_from_tray(self, icon) -> None:
        self._request_shutdown(stop_icon=False)
        icon.stop()

    def _request_shutdown(self, *, stop_icon: bool) -> None:
        if self._shutdown.is_set():
            return
        stop_strategy()
        close_all_gui()
        self._shutdown.set()
        if stop_icon and self._tray:
            self._tray.stop()

    def _handle_command(self, cmd: CommandName, request: dict) -> dict:
        if cmd == "ping":
            return {"ok": True, "message": "pong"}
        if cmd == "register_gui":
            pid = request.get("pid")
            if isinstance(pid, int):
                register_gui_pid(pid)
            else:
                register_gui_pid()
            return {"ok": True}
        if cmd == "status":
            return build_status_response()
        if cmd == "start":
            self._tray_start()
            status = get_runtime_status()
            if status.running:
                return {"ok": True, "message": "Zapret запущен."}
            return {"ok": False, "error": status.error or "Не удалось запустить zapret."}
        if cmd == "stop":
            ok, message = stop_strategy()
            return {"ok": ok, "message": message}
        if cmd == "open_ui":
            ok, message = launch_gui()
            return {"ok": ok, "message": message}
        if cmd == "shutdown":
            self._request_shutdown(stop_icon=True)
            return {"ok": True, "message": "Daemon завершает работу."}
        return {"ok": False, "error": f"unknown command: {cmd}"}


def run_daemon() -> None:
    TigoDaemon().run()


if __name__ == "__main__":
    run_daemon()
    sys.exit(0)
