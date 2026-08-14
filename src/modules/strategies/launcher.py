"""Build winws launch command from a strategy."""

from __future__ import annotations

import re
from pathlib import Path

from src.core.debug_log import debug
from src.core.paths import (
    bin_dir,
    flowseal_fake_bin_dir,
    flowseal_user_lists_dir,
    flowseal_version_lists_dir,
    program_root,
)
from src.core.settings import get_settings
from src.kernel.launch_spec import WinwsLaunchSpec, tokenize_winws_args
from src.modules.filters.game_filter import get_game_filter_ports, sync_game_filter_from_disk
from src.modules.filters.tcp import enable_tcp_timestamps
from src.modules.strategies.models import Strategy
from src.modules.strategies.parser import resolve_strategy_args


def _validate_assets(winws: Path, args: str) -> str | None:
    if not winws.exists():
        return f"winws.exe не найден: {winws}"
    for match in re.finditer(r'"([^"]+)"', args):
        candidate = Path(match.group(1))
        if candidate.suffix.lower() in {".bin", ".txt"} and not candidate.exists():
            return f"Файл не найден: {candidate}"
    return None


def ensure_runtime_preflight(*, version: str) -> tuple[bool, str]:
    winws = bin_dir() / "winws.exe"
    if not winws.exists():
        return False, f"winws.exe не найден: {winws}. Установите или обновите flowseal."
    if not any(bin_dir().glob("*.sys")):
        return False, "WinDivert64.sys не найден в bin/."
    sync_game_filter_from_disk(version)
    if not enable_tcp_timestamps():
        return False, "Не удалось включить TCP timestamps."
    debug("strategies", f"preflight ok for version {version}")
    return True, ""


def build_winws_launch(strategy: Strategy, *, version: str | None = None) -> tuple[WinwsLaunchSpec | None, str | None]:
    settings = get_settings()
    ver = version or settings.active_version
    if not ver:
        return None, "Не выбрана активная версия flowseal."

    ok, message = ensure_runtime_preflight(version=ver)
    if not ok:
        debug("strategies", message, level="error")
        return None, message

    winws = bin_dir() / "winws.exe"
    game_tcp, game_udp = get_game_filter_ports(settings.game_filter)
    args = resolve_strategy_args(
        strategy.args_template,
        bin_dir=flowseal_fake_bin_dir(),
        lists_dir=flowseal_version_lists_dir(ver),
        user_lists_dir=flowseal_user_lists_dir(),
        root_dir=program_root(),
        game_filter_tcp=game_tcp,
        game_filter_udp=game_udp,
    )
    missing = _validate_assets(winws, args)
    if missing:
        debug("strategies", missing, level="error")
        return None, missing

    spec = WinwsLaunchSpec(
        exe=winws,
        argv=tokenize_winws_args(args),
        cwd=bin_dir(),
        strategy_name=strategy.display_name,
        strategy_id=strategy.id,
    )
    debug("strategies", f"built launch spec for {strategy.name}: argv={spec.argv}")
    return spec, None


def build_custom_launch(args_text: str) -> tuple[WinwsLaunchSpec | None, str | None]:
    settings = get_settings()
    args = (args_text or settings.custom_strategy_args or "").strip()
    if not args:
        return None, "Укажите аргументы своей стратегии."

    winws = bin_dir() / "winws.exe"
    if not winws.exists():
        return None, f"winws.exe не найден: {winws}."
    if not any(bin_dir().glob("*.sys")):
        return None, "WinDivert64.sys не найден в bin/."
    if not enable_tcp_timestamps():
        return None, "Не удалось включить TCP timestamps."

    missing = _validate_assets(winws, args)
    if missing:
        return None, missing

    spec = WinwsLaunchSpec(
        exe=winws,
        argv=tokenize_winws_args(args),
        cwd=bin_dir(),
        strategy_name="custom",
        strategy_id="custom",
    )
    debug("strategies", f"built custom launch spec: argv={spec.argv}")
    return spec, None
