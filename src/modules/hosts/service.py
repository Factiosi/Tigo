"""Hosts editor actions for the UI."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass

import httpx

from src.core.debug_log import info, warn
from src.core.settings import get_settings, save_settings
from src.modules.dns.core import flush_dns_cache_native
from src.modules.hosts.catalog import Catalog, CatalogError, has_ipv6_route, load_catalog, service_rows
from src.modules.hosts.catalog_update import catalog_check_due, update_catalog
from src.modules.hosts.hosts_file import (
    DEFAULT_HOSTS,
    HostsSummary,
    backup_path,
    decode,
    hosts_path,
    read_hosts,
    set_block,
    summarize,
    write_hosts,
)
from src.modules.hosts.presets import PRESETS, HostsPreset

_ASSOCSTR_EXECUTABLE = 2
_SW_SHOWNORMAL = 1
_ACCESS_HINT = (
    "Нет доступа к файлу hosts. Его может защищать антивирус "
    "(в Защитнике Windows — «Изменение файла hosts»): разрешите изменение и повторите."
)


@dataclass(frozen=True)
class HostsState:
    summary: HostsSummary
    presets: list[tuple[HostsPreset, int]]  # preset, entries currently written (0 = off)
    has_backup: bool


def load_state() -> HostsState:
    summary = summarize(read_hosts())
    return HostsState(
        summary=summary,
        presets=[(preset, summary.blocks.get(preset.id, 0)) for preset in PRESETS],
        has_backup=backup_path().exists(),
    )


def _write(text: str, action: str) -> tuple[bool, str]:
    try:
        write_hosts(text)
    except PermissionError:
        warn("hosts", f"{action}: access denied")
        return False, _ACCESS_HINT
    except OSError as exc:
        warn("hosts", f"{action}: {exc}")
        return False, f"Не удалось записать hosts: {exc}"
    flush_dns_cache_native()
    info("hosts", action)
    return True, ""


def set_preset(preset_id: str, enabled: bool) -> tuple[bool, str]:
    preset = next((item for item in PRESETS if item.id == preset_id), None)
    if preset is None:
        return False, "Набор не найден."
    text = set_block(read_hosts(), preset.id, preset.rows() if enabled else None)
    ok, error = _write(text, f"preset {preset.id} {'on' if enabled else 'off'}")
    if not ok:
        return False, error
    return True, f"«{preset.title}»: {'включено' if enabled else 'выключено'}."


SERVICE_BLOCK_PREFIX = "svc-"


def service_block_id(service_id: str) -> str:
    return SERVICE_BLOCK_PREFIX + service_id.lower()


def _services_text(text: str, selection: dict[str, str], catalog: Catalog, *, ipv6: bool) -> tuple[str, int, list[str]]:
    """Rewrite every service block; return (text, entries written, names left empty)."""
    wanted = {service_block_id(sid) for sid in selection}
    for block_id in summarize(text).blocks:
        if block_id.startswith(SERVICE_BLOCK_PREFIX) and block_id not in wanted:
            text = set_block(text, block_id, None)
    written = 0
    empty: list[str] = []
    for service_id, profile_id in selection.items():
        service = catalog.service(service_id)
        rows = service_rows(catalog, service_id, profile_id, ipv6=ipv6) if service else []
        if service and not rows:
            empty.append(service.name)
        text = set_block(text, service_block_id(service_id), rows)
        written += len(rows)
    return text, written, empty


def apply_services(selection: dict[str, str]) -> tuple[bool, str]:
    """Write the chosen services into hosts and remember the choice."""
    try:
        catalog = load_catalog()
    except CatalogError as exc:
        return False, f"Каталог сервисов недоступен: {exc}"
    known = {sid: pid for sid, pid in selection.items() if catalog.service(sid)}
    text, written, empty = _services_text(read_hosts(), known, catalog, ipv6=has_ipv6_route())
    ok, error = _write(text, f"services applied: {len(known)} services, {written} entries")
    if not ok:
        return False, error
    settings = get_settings()
    settings.hosts_services = known
    save_settings(settings)
    message = f"Сервисы в hosts: {len(known)}, записей: {written}." if known else "Сервисы убраны из hosts."
    if empty:
        message += f" Без адресов (нужен IPv6?): {', '.join(empty)}."
    return True, message


def refresh_catalog_and_services(*, force: bool = False) -> tuple[bool, str]:
    """Fetch a newer catalog when due and rewrite the chosen services with it."""
    if not force and not catalog_check_due():
        return True, ""
    try:
        changed, message = update_catalog()
    except (CatalogError, httpx.HTTPError, OSError, ValueError) as exc:
        warn("hosts", f"catalog update failed: {exc}")
        return False, f"Не удалось обновить каталог сервисов: {exc}"
    selection = get_settings().hosts_services
    if changed and selection:
        ok, applied = apply_services(selection)
        return ok, f"{message} {applied}"
    return True, message


def restore_default() -> tuple[bool, str]:
    ok, error = _write(DEFAULT_HOSTS, "restored default hosts")
    if not ok:
        return False, error
    _forget_services()
    return True, "Файл hosts восстановлен к стандартному виду Windows."


def restore_backup() -> tuple[bool, str]:
    backup = backup_path()
    if not backup.exists():
        return False, "Резервной копии нет: Tigo ещё не менял hosts."
    ok, error = _write(decode(backup.read_bytes()), "restored hosts backup")
    if not ok:
        return False, error
    _forget_services()
    return True, "Файл hosts восстановлен из копии, снятой до первого изменения Tigo."


def _forget_services() -> None:
    """The file no longer has service blocks; keep the saved choice in step."""
    settings = get_settings()
    if settings.hosts_services:
        settings.hosts_services = {}
        save_settings(settings)


def default_text_editor() -> str:
    """Executable registered for .txt files, Notepad when there is none."""
    buffer = ctypes.create_unicode_buffer(1024)
    size = wintypes.DWORD(len(buffer))
    result = ctypes.windll.shlwapi.AssocQueryStringW(
        0, _ASSOCSTR_EXECUTABLE, ".txt", "open", buffer, ctypes.byref(size)
    )
    if result == 0 and buffer.value and os.path.isfile(buffer.value):
        return buffer.value
    return "notepad.exe"


def open_in_editor() -> tuple[bool, str]:
    """Open hosts in the default text editor, elevated so it can save the file."""
    editor = default_text_editor()
    code = ctypes.windll.shell32.ShellExecuteW(None, "runas", editor, f'"{hosts_path()}"', None, _SW_SHOWNORMAL)
    if code <= 32 and editor != "notepad.exe":
        warn("hosts", f"{editor} did not start elevated ({code}), falling back to Notepad")
        editor = "notepad.exe"
        code = ctypes.windll.shell32.ShellExecuteW(None, "runas", editor, f'"{hosts_path()}"', None, _SW_SHOWNORMAL)
    if code <= 32:
        return False, f"Не удалось открыть редактор (код {code})."
    name = os.path.splitext(os.path.basename(editor))[0]
    return True, f"Файл hosts открыт в {name} от имени администратора. После сохранения нажмите «Обновить»."
