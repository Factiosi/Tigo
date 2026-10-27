"""Hosts editor actions for the UI."""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.core.debug_log import info, warn
from src.modules.dns.core import flush_dns_cache_native
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


def restore_default() -> tuple[bool, str]:
    ok, error = _write(DEFAULT_HOSTS, "restored default hosts")
    return (True, "Файл hosts восстановлен к стандартному виду Windows.") if ok else (False, error)


def restore_backup() -> tuple[bool, str]:
    backup = backup_path()
    if not backup.exists():
        return False, "Резервной копии нет: Tigo ещё не менял hosts."
    ok, error = _write(decode(backup.read_bytes()), "restored hosts backup")
    return (True, "Файл hosts восстановлен из копии, снятой до первого изменения Tigo.") if ok else (False, error)


def open_in_editor() -> tuple[bool, str]:
    """Open hosts in Notepad; Tigo runs elevated, so Notepad can save it."""
    try:
        os.startfile("notepad.exe", arguments=str(hosts_path()))  # type: ignore[attr-defined]
    except OSError as exc:
        return False, str(exc)
    return True, "Файл hosts открыт в Блокноте. После сохранения обновите страницу."
