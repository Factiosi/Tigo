"""Kernel public API — start/stop winws by launch spec."""

from __future__ import annotations

from src.core.debug_log import debug
from src.core.paths import bin_dir
from src.core.settings import get_settings, save_settings
from src.kernel import runtime_state
from src.kernel.launch_spec import WinwsLaunchSpec
from src.kernel.migrate import migrate_legacy_service
from src.kernel.runtime_state import RuntimePhase, RuntimeStatus
from src.kernel.windivert_cleanup import cleanup_windivert_services
from src.kernel.winws_runner import get_runner
from src.modules.strategies.launcher import build_custom_launch, build_winws_launch
from src.modules.strategies.models import Strategy
from src.modules.strategies.repository import list_strategies


def initialize_runtime() -> None:
    debug("kernel", "initialize_runtime")
    migrate_legacy_service()
    sys_present = bin_dir().exists() and any(bin_dir().glob("*.sys"))
    runtime_state.set_windivert_present(sys_present)
    debug("kernel", f"windivert present={sys_present}")


def get_runtime_status() -> RuntimeStatus:
    return runtime_state.get_status()


def get_effective_runtime_status() -> RuntimeStatus:
    """Return daemon status over IPC when background process is active."""
    try:
        from src.daemon.ipc import daemon_status, is_daemon_running

        if is_daemon_running():
            remote = daemon_status()
            if remote is not None:
                try:
                    phase = RuntimePhase(remote.phase)
                except ValueError:
                    phase = RuntimePhase.IDLE
                local = runtime_state.get_status()
                return RuntimeStatus(
                    phase=phase,
                    running=remote.running or phase == RuntimePhase.RUNNING,
                    strategy_name=remote.strategy_name or None,
                    pid=remote.pid,
                    windivert_sys_present=local.windivert_sys_present,
                    error=remote.error or None,
                    tests_running=remote.tests_running,
                )
    except ImportError:
        pass
    return runtime_state.get_status()


def start(spec: WinwsLaunchSpec) -> tuple[bool, str]:
    debug("kernel", f"start requested: {spec.strategy_name} argv={spec.argv}")
    ok, message = get_runner().start(spec)
    if ok:
        debug("kernel", f"started pid={get_runner().snapshot().pid}: {message}")
    else:
        debug("kernel", f"start failed: {message}", level="error")
    return ok, message


def stop(*, cleanup_windivert: bool = True) -> tuple[bool, str]:
    debug("kernel", "stop requested")
    ok, message = get_runner().stop()
    if cleanup_windivert:
        cleanup_windivert_services()
        debug("kernel", "windivert cleanup done")
    debug("kernel", f"stop result: {message}")
    return ok, message


def start_strategy(strategy: Strategy) -> tuple[bool, str]:
    spec, error = build_winws_launch(strategy)
    if error or spec is None:
        return False, error or "Не удалось собрать команду запуска."

    ok, message = start(spec)
    if ok:
        settings = get_settings()
        settings.selected_strategy = strategy.id
        save_settings(settings)
    return ok, message


def stop_strategy(*, cleanup_windivert: bool = True) -> tuple[bool, str]:
    return stop(cleanup_windivert=cleanup_windivert)


def start_custom_strategy(args_text: str | None = None) -> tuple[bool, str]:
    spec, error = build_custom_launch(args_text or "")
    if error or spec is None:
        return False, error or "Не удалось собрать команду запуска."
    ok, message = start(spec)
    if ok:
        settings = get_settings()
        if args_text is not None:
            settings.custom_strategy_args = args_text.strip()
        save_settings(settings)
    return ok, message


def restart_if_running(*, strategy_id: str | None = None) -> tuple[bool, str]:
    """Stop and restart the active strategy if winws is currently running."""
    try:
        from src.daemon.ipc import daemon_start, daemon_stop, is_daemon_running

        if is_daemon_running():
            status = get_effective_runtime_status()
            if not status.running:
                return True, ""
            ok, msg = daemon_stop()
            if not ok:
                return False, msg
            settings = get_settings()
            launch_id = strategy_id or settings.selected_strategy
            return daemon_start(launch_id)
    except ImportError:
        pass

    status = get_runtime_status()
    if not status.running:
        return True, ""

    stop(cleanup_windivert=False)
    settings = get_settings()
    if settings.strategy_source == "custom":
        return start_custom_strategy(settings.custom_strategy_args)

    launch_id = strategy_id or settings.selected_strategy
    if not launch_id:
        return False, "Стратегия не выбрана."

    for strategy in list_strategies():
        if strategy.id == launch_id:
            return start_strategy(strategy)
    return False, "Выбранная стратегия не найдена."
