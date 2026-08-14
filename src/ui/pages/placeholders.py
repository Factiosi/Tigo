"""Placeholder pages for upcoming features."""

from __future__ import annotations

import flet as ft

from src.theme import T
from src.ui.components import scroll_page, ui_text


def placeholder_page(description: str) -> ft.Control:
    return scroll_page(
        ui_text(description, color=T.TEXT_MUTED),
    )
