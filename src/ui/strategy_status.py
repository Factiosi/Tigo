"""Shared presentation helpers for strategy test status."""

from __future__ import annotations

import flet as ft

from src.modules.strategy_testing import results as tr
from src.ui.components import status_pill


def strategy_status(strategy_id: str) -> tuple[str, str]:
    item = tr.get_result(strategy_id)
    if not item:
        return "offline", "Не протестирована"
    mapping = {
        "full": ("active", "Полностью работает (лучший выбор)"),
        "partial": ("expiring", "Частично работает"),
        "failed": ("error", "Не работает"),
        "unknown": ("error", "Неизвестно"),
        "running": ("expiring", "Проверяется"),
    }
    return mapping.get(item.state, ("offline", "Не протестирована"))


def strategy_actions_disabled(
    strategy_id: str,
    *,
    selected_strategy: str | None,
    tests_running: bool,
) -> bool:
    return (
        tests_running
        or not tr.is_tested(strategy_id)
        or selected_strategy == strategy_id
    )


def strategy_status_pill(strategy_id: str, *, compact: bool = False) -> ft.Control:
    key, label = strategy_status(strategy_id)
    if compact:
        compact_labels = {
            "Полностью работает (лучший выбор)": "Работает",
            "Частично работает": "Частично",
            "Не протестирована": "Нет теста",
            "Проверяется": "Проверяется",
            "Не работает": "Не работает",
            "Неизвестно": "Неизвестно",
        }
        label = compact_labels.get(label, label)
    return status_pill(key, label, dense=compact)

