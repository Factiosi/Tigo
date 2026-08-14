"""Flowseal update orchestration — shared by settings, startup and daemon."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Callable

from src.core.events import emit
from src.core.debug_log import debug, info as log_info
from src.core.paths import runtime_installed, runtime_version_path, staging_dir
from src.core.settings import get_settings, save_settings
from src.kernel.public import get_effective_runtime_status
from src.modules.filters.game_filter import sync_game_filter_from_disk
from src.modules.filters.ipset_filter import sync_ipset_from_disk
from src.modules.strategies.repository import (
    apply_version_retention,
    has_flowseal_strategies,
    set_active_version,
    write_version_meta,
)
from src.modules.updates.github import (
    check_for_update,
    download_release_to_staging,
    fetch_latest_release_asset_url,
)
from src.modules.updates.transformer import promote_staging, transform_runtime

MessageCallback = Callable[[str, bool], None]

MSG_UP_TO_DATE = "У вас последняя актуальная версия стратегий"
MSG_UPDATE_AVAILABLE = "Доступна новая версия стратегий"
MSG_DOWNLOADING = "Новая версия стратегий доступна и скачивается"
MSG_STALE_REMOVED = "Неактуальные версии стратегий удалены"


@dataclass
class ApplyResult:
    ok: bool
    message: str
    toast_kind: str = "info"
    version_changed: bool = False
    applied_tag: str | None = None


def format_check_message(info) -> tuple[bool, str, str]:
    if info.error and not info.update_available:
        return False, info.error, "error"
    if info.update_available:
        return True, MSG_UPDATE_AVAILABLE, "warning"
    return True, MSG_UP_TO_DATE, "success"


def check_only() -> tuple[bool, str, str]:
    settings = get_settings()
    info = check_for_update(settings.active_version)
    return format_check_message(info)


def ensure_runtime_installed() -> ApplyResult:
    """Install the mandatory winws runtime independently from strategy settings."""
    if runtime_installed():
        return ApplyResult(True, "Runtime уже установлен.", toast_kind="success")

    tag, url = fetch_latest_release_asset_url()
    if not url or not tag:
        return ApplyResult(
            False,
            "Не удалось найти runtime в официальном релизе Flowseal на GitHub.",
            toast_kind="error",
        )

    staging = staging_dir()
    try:
        source = download_release_to_staging(url, tag)
        transform_runtime(source)
        if not runtime_installed():
            return ApplyResult(
                False,
                "Архив Flowseal загружен, но bin/winws.exe в нём не найден.",
                toast_kind="error",
            )
        runtime_version_path().write_text(tag + "\n", encoding="utf-8")
        log_info("updates", f"installed mandatory runtime from Flowseal {tag}")
        return ApplyResult(
            True,
            f"Runtime Flowseal {tag} установлен.",
            toast_kind="success",
            applied_tag=tag,
        )
    except Exception as exc:  # noqa: BLE001
        debug("updates", f"runtime install failed: {exc}", level="error")
        return ApplyResult(False, f"Не удалось установить runtime: {exc}", toast_kind="error")
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def check_and_apply(*, restart_running: bool = True) -> ApplyResult:
    settings = get_settings()
    missing_local = not has_flowseal_strategies() or not runtime_installed()
    info = check_for_update(None if missing_local else settings.active_version)
    if info.error and not info.update_available:
        return ApplyResult(False, info.error, toast_kind="error")
    if not info.update_available:
        return ApplyResult(True, MSG_UP_TO_DATE, toast_kind="success")

    tag, url = fetch_latest_release_asset_url()
    if not url or not tag:
        return ApplyResult(False, "Не удалось найти архив релиза на GitHub.", toast_kind="error")

    was_running = restart_running and get_effective_runtime_status().running
    if was_running:
        from src.daemon.ipc import daemon_stop

        stopped, stop_message = daemon_stop()
        if not stopped:
            return ApplyResult(
                False,
                f"Не удалось остановить zapret перед обновлением: {stop_message}",
                toast_kind="error",
            )

    staging = staging_dir()
    try:
        source = download_release_to_staging(url, tag)
        promote_staging(source, tag, skip_list_updates=settings.skip_list_updates)
        write_version_meta(tag)
        previous = settings.active_version
        set_active_version(tag)
        apply_version_retention()
        sync_game_filter_from_disk(tag)
        sync_ipset_from_disk(tag)
        version_changed = previous != tag
        if was_running:
            from src.daemon.ipc import daemon_start

            ok, msg = daemon_start()
            if not ok:
                return ApplyResult(
                    False,
                    f"Версия {tag} установлена, но перезапуск не удался: {msg}",
                    toast_kind="error",
                    version_changed=True,
                    applied_tag=tag,
                )
        log_info("updates", f"applied flowseal version {tag}")
        emit("strategies_changed")
        return ApplyResult(
            True,
            MSG_UP_TO_DATE,
            toast_kind="success",
            version_changed=version_changed,
            applied_tag=tag,
        )
    except Exception as exc:  # noqa: BLE001
        debug("updates", f"apply failed: {exc}", level="error")
        if was_running:
            from src.daemon.ipc import daemon_start

            daemon_start()
        return ApplyResult(False, str(exc), toast_kind="error")
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def run_startup_updates(on_message: MessageCallback | None = None) -> None:
    settings = get_settings()
    if settings.strategy_source != "flowseal":
        return
    if not settings.auto_check_updates_on_startup and not settings.auto_promote_updates:
        return

    info_obj = check_for_update(settings.active_version)
    if settings.auto_check_updates_on_startup and on_message:
        ok, msg, kind = format_check_message(info_obj)
        on_message(msg, error=not ok or kind == "error")

    if settings.auto_promote_updates and (
        info_obj.update_available or not has_flowseal_strategies() or not runtime_installed()
    ):
        result = check_and_apply()
        if on_message:
            on_message(result.message, error=not result.ok)
