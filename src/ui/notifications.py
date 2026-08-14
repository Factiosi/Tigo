"""Top toast banners — Factiosi feedback pattern for Tigo."""

from __future__ import annotations

import threading

import flet as ft

from src.theme import T
from src.ui.components import ANIM_FAST, ui_text

_active_toast: ft.Container | None = None
_dismiss_timer: threading.Timer | None = None

_KIND_STYLES: dict[str, tuple[str, str]] = {
    "info": (T.ACCENT, T.ACCENT_SOFT),
    "success": (T.STATUS_ACTIVE, T.STATUS_ACTIVE_BG),
    "warning": (T.STATUS_EXPIRING, T.STATUS_EXPIRING_BG),
    "error": (T.STATUS_ERROR, T.STATUS_ERROR_BG),
}


def _cancel_timer() -> None:
    global _dismiss_timer
    if _dismiss_timer is not None:
        _dismiss_timer.cancel()
        _dismiss_timer = None


def _remove_toast(page: ft.Page) -> None:
    global _active_toast
    _cancel_timer()
    if _active_toast is not None and _active_toast in page.overlay:
        page.overlay.remove(_active_toast)
    _active_toast = None
    try:
        page.update()
    except RuntimeError:
        pass


def show_toast(
    page: ft.Page,
    message: str,
    *,
    kind: str = "info",
    duration: float = 4.5,
) -> None:
    """Show a short banner at the top of the window."""
    global _active_toast, _dismiss_timer

    text = message.strip()
    if not text:
        return

    fg, bg = _KIND_STYLES.get(kind, _KIND_STYLES["info"])
    banner = ft.Container(
        content=ft.Row(
            [
                ft.Container(width=6, height=6, bgcolor=fg, border_radius=99),
                ui_text(text, size=T.FONT_BODY, color=fg, expand=True),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=bg,
        border=ft.Border.all(1, T.BORDER),
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        shadow=ft.BoxShadow(
            blur_radius=18,
            spread_radius=0,
            color="#00000055",
            offset=ft.Offset(0, 6),
        ),
        top=10,
        left=24,
        right=24,
        animate_opacity=ANIM_FAST,
        opacity=1,
    )

    _remove_toast(page)
    _active_toast = banner
    page.overlay.append(banner)
    page.update()

    def dismiss() -> None:
        try:
            page.run_thread(lambda: _remove_toast(page))
        except AttributeError:
            _remove_toast(page)

    _dismiss_timer = threading.Timer(duration, dismiss)
    _dismiss_timer.daemon = True
    _dismiss_timer.start()
