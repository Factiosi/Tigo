"""Standalone debug console process."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft

from src.core.debug_log import clear, get_persistent_text
from src.core.fonts import FONT_JETBRAINS_MONO, register_mono_font
from src.core.paths import APP_NAME
from src.core.settings import get_settings
from src.core.version import __version__
from src.theme import T, apply_theme, build_flet_theme, build_theme_tokens
from src.ui.components import BUTTON_HEIGHT

_MONO = FONT_JETBRAINS_MONO
_CORNER_INSET = 12
_BOTTOM_EPSILON = 6.0
_WHEEL_NOTCH_PX = 40.0
_UNPIN_WHEEL_NOTCHES = 2


def _session_closed(exc: BaseException) -> bool:
    return isinstance(exc, RuntimeError) and "Session closed" in str(exc)


def main(page: ft.Page) -> None:
    settings = get_settings()
    apply_theme(settings.theme_mode, settings.portal_hue)
    register_mono_font(page)
    page.title = f"{APP_NAME} {__version__} — консоль отладки"
    page.bgcolor = T.GROUND
    page.theme = build_flet_theme(build_theme_tokens("light", settings.portal_hue))
    page.dark_theme = build_flet_theme(build_theme_tokens("dark", settings.portal_hue))
    page.theme_mode = ft.ThemeMode.DARK if settings.theme_mode == "dark" else ft.ThemeMode.LIGHT
    page.window.width = 900
    page.window.height = 500
    page.window.min_width = 480
    page.window.min_height = 240
    page.padding = 0

    log_text = ft.Text(
        " ",
        size=12,
        color=T.TEXT,
        font_family=_MONO,
        selectable=True,
    )

    stick_to_bottom = True
    at_bottom = True
    up_from_bottom_px = 0.0
    programmatic_scroll = False
    alive = True

    def stop_polling(_: ft.ControlEvent | None = None) -> None:
        nonlocal alive
        alive = False

    page.on_disconnect = stop_polling

    log_scroller = ft.Column(
        [log_text],
        expand=True,
        scroll=ft.ScrollMode.ALWAYS,
        auto_scroll=False,
        spacing=0,
    )

    async def scroll_to_bottom() -> None:
        nonlocal programmatic_scroll, alive
        if not alive:
            return
        programmatic_scroll = True
        try:
            await log_scroller.scroll_to(offset=-1, duration=0)
        except RuntimeError as exc:
            if _session_closed(exc):
                alive = False
                return
            raise
        finally:
            programmatic_scroll = False

    async def refresh(*, force_bottom: bool = False) -> None:
        nonlocal stick_to_bottom, at_bottom, up_from_bottom_px, alive
        if not alive:
            return
        log_text.value = get_persistent_text() or " "
        if force_bottom:
            stick_to_bottom = True
            at_bottom = True
            up_from_bottom_px = 0.0
        try:
            page.update()
        except RuntimeError as exc:
            if _session_closed(exc):
                alive = False
                return
            raise
        if stick_to_bottom and (at_bottom or force_bottom):
            await asyncio.sleep(0)
            await scroll_to_bottom()
            if alive:
                at_bottom = True

    def on_scroll(e: ft.OnScrollEvent) -> None:
        nonlocal stick_to_bottom, at_bottom, up_from_bottom_px
        if programmatic_scroll:
            return

        at_bottom = e.extent_after <= _BOTTOM_EPSILON

        if at_bottom:
            stick_to_bottom = True
            up_from_bottom_px = 0.0
            return

        if not stick_to_bottom:
            return

        delta = e.scroll_delta
        if delta is None or delta >= 0:
            return

        up_from_bottom_px += abs(delta)
        if up_from_bottom_px >= _WHEEL_NOTCH_PX * _UNPIN_WHEEL_NOTCHES:
            stick_to_bottom = False

    log_scroller.on_scroll = on_scroll

    async def clear_and_refresh(_: ft.ControlEvent) -> None:
        clear()
        await refresh(force_bottom=True)

    def on_clear_click(e: ft.ControlEvent) -> None:
        page.run_task(clear_and_refresh, e)

    async def poll_logs() -> None:
        while alive:
            await asyncio.sleep(1.0)
            if not alive:
                break
            try:
                await refresh()
            except RuntimeError as exc:
                if _session_closed(exc):
                    stop_polling()
                    break
                raise

    clear_btn = ft.FilledButton(
        "Очистить",
        on_click=on_clear_click,
        height=BUTTON_HEIGHT,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: T.ELEVATED,
                ft.ControlState.DISABLED: T.ELEVATED,
            },
            color={
                ft.ControlState.DEFAULT: T.TEXT,
                ft.ControlState.DISABLED: T.TEXT_MUTED,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(1, T.BORDER),
                ft.ControlState.DISABLED: ft.BorderSide(1, T.BORDER),
            },
            shape=ft.RoundedRectangleBorder(radius=T.RADIUS_PILL),
            padding=ft.Padding.symmetric(horizontal=14, vertical=0),
            text_style=ft.TextStyle(
                size=T.FONT_CAPTION,
                font_family=T.FONT_FAMILY,
                weight=ft.FontWeight.W_500,
            ),
            elevation=0,
            overlay_color={
                ft.ControlState.HOVERED: T.ACCENT_SOFT,
                ft.ControlState.FOCUSED: T.ACCENT_SOFT,
                ft.ControlState.PRESSED: T.ACCENT_SOFT,
            },
        ),
    )

    page.add(
        ft.Stack(
            [
                ft.Container(
                    content=ft.SelectionArea(content=log_scroller),
                    expand=True,
                    padding=ft.Padding.all(_CORNER_INSET),
                    bgcolor=T.GROUND,
                ),
                ft.Container(
                    content=clear_btn,
                    top=_CORNER_INSET,
                    right=_CORNER_INSET,
                ),
            ],
            expand=True,
            fit=ft.StackFit.EXPAND,
        )
    )
    page.run_task(refresh, force_bottom=True)
    page.run_task(poll_logs)


if __name__ == "__main__":
    ft.run(main)
