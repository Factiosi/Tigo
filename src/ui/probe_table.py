"""Probe results table — compact UI rows (not selectable text)."""

from __future__ import annotations

import re

import flet as ft

from src.modules.strategy_testing import results as tr
from src.theme import T
from src.ui.components import ui_text

NAME_WIDTH = 132
HTTP_WIDTH = 56
TLS_WIDTH = 62
PING_WIDTH = 72
PROBE_FONT_SIZE = 12
_LABEL_COLOR = T.TEXT_MUTED


def factiosi_spinner(*, size: int = 11) -> ft.ProgressRing:
    return ft.ProgressRing(
        width=size,
        height=size,
        stroke_width=2,
        color=T.ACCENT,
        bgcolor=T.ACCENT_SOFT,
    )


def _metric_value(raw: str) -> str:
    if ":" in raw:
        return raw.split(":", 1)[1]
    return raw


def _token_color(raw: str) -> str:
    value = _metric_value(raw).strip()
    upper = value.upper()
    if upper == "OK":
        return T.STATUS_ACTIVE
    if upper in {"?", ""}:
        return T.TEXT_FAINT
    if upper in {"ERROR", "ERR"}:
        return T.STATUS_ERROR
    if "UNSUP" in upper:
        return T.STATUS_EXPIRING
    if any(x in upper for x in ("SSL", "FAIL", "TIMEOUT")):
        return T.STATUS_ERROR
    if value.lower() in {"timeout", "n/a"}:
        return T.STATUS_EXPIRING
    return T.TEXT


def _parse_ping_ms(text: str) -> int | None:
    match = re.search(r"(\d+)", text.replace(" ", ""))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _ping_value_color(text: str) -> str:
    upper = text.upper()
    if any(x in upper for x in ("ERROR", "FAIL", "TIMEOUT")) or upper.strip() in {"N/A", "?"}:
        return T.STATUS_ERROR
    ms = _parse_ping_ms(text)
    if ms is None:
        return T.TEXT
    if ms >= 200:
        return T.STATUS_ERROR
    if ms > 100:
        return T.STATUS_EXPIRING
    return T.STATUS_ACTIVE


def _short_token(raw: str) -> str:
    value = _metric_value(raw)
    if value == "?":
        return "?"
    if value == "OK":
        return "OK"
    if value == "ERROR":
        return "ERR"
    if value == "UNSUP":
        return "UNSUP"
    if value == "SSL":
        return "SSL"
    return value


def _labeled_value(label: str, value: str, *, value_color: str) -> ft.Control:
    return ft.Row(
        [
            ui_text(f"{label}:", size=PROBE_FONT_SIZE, color=_LABEL_COLOR, no_wrap=True),
            ui_text(value, size=PROBE_FONT_SIZE, color=value_color, no_wrap=True),
        ],
        spacing=0,
        tight=True,
    )


def _metric_cell(label: str, cell: tr.ProbeCell, *, width: int) -> ft.Container:
    if cell.phase == "loading":
        content: ft.Control = ft.Row(
            [
                ui_text(f"{label}:", size=PROBE_FONT_SIZE, color=_LABEL_COLOR, no_wrap=True),
                factiosi_spinner(size=10),
            ],
            spacing=4,
            tight=True,
        )
    elif cell.phase == "pending" or cell.text == "?":
        content = _labeled_value(label, "?", value_color=T.TEXT_FAINT)
    else:
        value = _short_token(cell.text)
        content = _labeled_value(label, value, value_color=_token_color(cell.text))
    return ft.Container(content=content, width=width)


def _ping_cell(cell: tr.ProbeCell) -> ft.Container:
    if cell.phase == "loading":
        content: ft.Control = ft.Row(
            [
                ui_text("Ping:", size=PROBE_FONT_SIZE, color=_LABEL_COLOR, no_wrap=True),
                factiosi_spinner(size=10),
            ],
            spacing=4,
            tight=True,
        )
    elif cell.phase == "pending" or cell.text in {"?", "? ms"}:
        content = _labeled_value("Ping", "?", value_color=T.TEXT_FAINT)
    else:
        ping = cell.text.replace(" ", "")
        content = _labeled_value("Ping", ping, value_color=_ping_value_color(cell.text))
    return ft.Container(content=content, width=PING_WIDTH)


def _probe_row(row: tr.ProbeTableRow) -> ft.Control:
    cells: list[ft.Control] = [
        ft.Container(
            content=ui_text(row.name, size=PROBE_FONT_SIZE, color=T.TEXT, no_wrap=True),
            width=NAME_WIDTH,
        ),
    ]
    if row.http is not None:
        cells.extend(
            [
                _metric_cell("HTTP", row.http, width=HTTP_WIDTH),
                _metric_cell("TLS1.2", row.tls12, width=TLS_WIDTH),
                _metric_cell("TLS1.3", row.tls13, width=TLS_WIDTH),
            ]
        )
    cells.append(_ping_cell(row.ping))
    return ft.Container(
        content=ft.Row(cells, spacing=4, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding.symmetric(vertical=2),
    )


def build_probe_table(strategy_id: str) -> ft.Control:
    item = tr.get_result(strategy_id)
    rows = tr.get_probe_table(strategy_id)
    if not rows:
        rows = tr.default_probe_table()

    table = ft.Column(
        [_probe_row(row) for row in rows],
        spacing=0,
        tight=True,
    )
    if item and item.detail.strip() and not tr.get_probe_table(strategy_id):
        return ft.Column(
            [
                ui_text(item.detail.strip(), size=PROBE_FONT_SIZE, color=T.STATUS_ERROR),
                table,
            ],
            spacing=6,
            tight=True,
        )
    return table
