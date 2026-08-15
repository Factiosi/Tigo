"""Blocking overlay while Tigo self-update installer runs."""

from __future__ import annotations

import flet as ft

from src.theme import T
from src.ui.components import ui_text
from src.ui.probe_table import factiosi_spinner

_OVERLAY: ft.Container | None = None

UPDATE_OVERLAY_MESSAGE = (
    "Подождите немного, идёт установка обновления, "
    "по завершению окно программы откроется..."
)


def show_update_install_overlay(page: ft.Page) -> None:
    global _OVERLAY
    hide_update_install_overlay(page)

    card = ft.Container(
        content=ft.Column(
            [
                factiosi_spinner(size=28),
                ui_text(
                    UPDATE_OVERLAY_MESSAGE,
                    size=T.FONT_BODY,
                    color=T.TEXT,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            tight=True,
        ),
        bgcolor=T.SURFACE,
        border=ft.Border.all(1, T.BORDER),
        border_radius=16,
        padding=ft.Padding.symmetric(horizontal=32, vertical=28),
        width=420,
    )
    _OVERLAY = ft.Container(
        content=ft.Container(
            content=card,
            alignment=ft.Alignment.CENTER,
            expand=True,
        ),
        bgcolor="#CC000000",
        expand=True,
        alignment=ft.Alignment.CENTER,
    )
    page.overlay.append(_OVERLAY)
    page.update()


def hide_update_install_overlay(page: ft.Page) -> None:
    global _OVERLAY
    if _OVERLAY is not None and _OVERLAY in page.overlay:
        page.overlay.remove(_OVERLAY)
    _OVERLAY = None
    try:
        page.update()
    except RuntimeError:
        pass
