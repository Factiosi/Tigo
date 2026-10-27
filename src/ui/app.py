"""Tigo application shell."""

from __future__ import annotations

import asyncio
import threading

import flet as ft

from src.core.branding import app_window_icon_path
from src.core.process_label import schedule_flet_process_label
from src.core.events import subscribe, unsubscribe
from src.core.fonts import register_mono_font
from src.core.paths import APP_NAME, is_packaged_app
from src.core.version import __version__
from src.core.settings import get_settings, save_settings
from src.modules.strategies.repository import has_flowseal_strategies
from src.modules.updates.app import (
    MSG_APP_UP_TO_DATE,
    check_and_install_app,
    check_app_only,
)
from src.ui.theme import T, apply_theme, build_flet_theme, build_theme_tokens
from src.modules.lifecycle.public import (
    handle_window_close,
    should_launch_gui,
    should_start_hidden,
    start_daemon_watchdog,
)
from src.ui.components import ANIM, close_active_select, lucide_icon, ui_text
from src.ui.pages.dns import DnsPage
from src.ui.pages.home import HomePage
from src.ui.pages.hosts import HostsPage
from src.ui.pages.lists import ListsPage
from src.ui.pages.strategies import StrategiesPage
from src.ui.pages.settings import SettingsPage
from src.ui.pages.tg_ws_proxy import TgWsProxyPage
from src.ui.notifications import present_app_update_result


def build_nav_items() -> list[tuple[str, str, str]]:
    """(route, label, Lucide icon name)."""
    settings = get_settings()
    items: list[tuple[str, str, str]] = [("home", "Главный экран", "house")]
    if settings.strategy_source == "flowseal":
        if has_flowseal_strategies(settings):
            items.append(("strategies", "Подбор стратегий", "flask-conical"))
        items.append(("lists", "Редактирование листов", "file-cog"))
    items.extend(
        [
            ("dns", "Изменение DNS", "columns-3-cog"),
            ("hosts", "Редактирование hosts", "server-cog"),
            ("tg_ws_proxy", "TG WS Proxy", "send"),
        ]
    )
    return items


class TigoApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self._route = "home"
        self._nav_controls: list[ft.Container] = []
        self._body = ft.Container()
        self._title = ft.Text()
        self._home_page: HomePage | None = None
        self._strategies_page: StrategiesPage | None = None
        self._strategies_changed_handler = self._on_strategies_changed
        self._app_update_started = False
        self._rail_sheen: ft.Container | None = None

    def _on_strategies_changed(self) -> None:
        if not self.page:
            return
        try:
            self.page.run_thread(self._reload_shell)
        except AttributeError:
            self._reload_shell()

    def _reset_shell(self) -> None:
        self._body = ft.Container(expand=True, bgcolor=T.GROUND, animate_opacity=ANIM)
        self._title = ui_text(
            "",
            size=T.FONT_TITLE,
            weight=ft.FontWeight.W_600,
            family=T.FONT_DISPLAY,
        )
        self._home_page = None
        self._strategies_page = None

    def show(self, *, initial_index: int = 0) -> None:
        settings = get_settings()
        apply_theme(settings.theme_mode, settings.portal_hue)
        self._reset_shell()
        self._configure_page()
        start_daemon_watchdog(self.page)
        nav = build_nav_items()
        if 0 <= initial_index < len(nav):
            self._route = nav[initial_index][0]
        elif initial_index >= len(nav):
            self._route = "settings"
        self._build_layout()
        unsubscribe("strategies_changed", self._strategies_changed_handler)
        subscribe("strategies_changed", self._strategies_changed_handler)
        self._navigate(self._route)
        self._start_app_update_check()
        self._start_rail_sheen()

    def _start_app_update_check(self) -> None:
        settings = get_settings()
        if (
            self._app_update_started
            or not is_packaged_app()
            or not settings.auto_check_app_updates_on_startup
        ):
            return
        self._app_update_started = True
        auto_install = settings.auto_install_app_updates

        def work() -> None:
            result = (
                check_and_install_app()
                if auto_install
                else check_app_only()
            )
            ok, message, kind = result
            if ok and message == MSG_APP_UP_TO_DATE:
                return
            if auto_install and ok and kind == "success":
                return

            def notify() -> None:
                present_app_update_result(self.page, ok, message, kind)

            try:
                self.page.run_thread(notify)
            except AttributeError:
                notify()

        threading.Thread(
            target=work,
            daemon=True,
            name="tigo-app-update-check",
        ).start()

    def _configure_page(self) -> None:
        page = self.page
        settings = get_settings()
        register_mono_font(page)
        page.title = APP_NAME
        schedule_flet_process_label(page, APP_NAME)
        page.bgcolor = T.GROUND
        page.theme = build_flet_theme(build_theme_tokens("light", settings.portal_hue))
        page.dark_theme = build_flet_theme(build_theme_tokens("dark", settings.portal_hue))
        page.theme_mode = (
            ft.ThemeMode.DARK if settings.theme_mode == "dark" else ft.ThemeMode.LIGHT
        )
        page.padding = 0
        page.window.width = 1040
        page.window.height = 760
        page.window.min_width = 860
        page.window.min_height = 600
        if should_start_hidden():
            page.window.visible = False
            page.window.minimized = True
        if settings.close_action == "minimize_tray":
            page.window.prevent_close = True
            page.window.on_event = self._on_window_event
        else:
            page.window.prevent_close = False
        icon_path = app_window_icon_path()
        if icon_path is not None:
            page.window.icon = str(icon_path)

    def _on_window_event(self, e: ft.WindowEvent) -> None:
        if e.type != ft.WindowEventType.CLOSE:
            return
        settings = get_settings()
        if handle_window_close(self.page, settings.close_action):

            async def close_window() -> None:
                if self._home_page:
                    self._home_page.stop()
                if self._strategies_page:
                    self._strategies_page.stop()
                await self.page.window.destroy()

            self.page.run_task(close_window)
            return

        async def close_window() -> None:
            await self.page.window.destroy()

        self.page.run_task(close_window)

    def _start_rail_sheen(self) -> None:
        """Один таймер блика на окно. Смена пункта его не перезапускает: блик идёт по своим часам."""
        page = self.page
        page._tigo_rail_app = self  # type: ignore[attr-defined]
        if getattr(page, "_tigo_rail_sheen_started", False):
            return
        page._tigo_rail_sheen_started = True  # type: ignore[attr-defined]

        def place(left: float, animation: ft.Animation | None) -> None:
            app = getattr(page, "_tigo_rail_app", None)
            sheen = app._rail_sheen if app else None
            if sheen is None or not sheen.page:
                return
            sheen.animate_position = animation
            sheen.left = left
            try:
                sheen.update()
            except Exception:
                pass

        # Проход анимирует сам Flutter с частотой экрана; Python лишь возвращает блик на старт.
        async def loop() -> None:
            while True:
                period = T.RAIL_SHEEN_PERIOD
                passage = period * 0.15
                place(-96, None)
                await asyncio.sleep(0.1)
                place(T.SIDEBAR_WIDTH, ft.Animation(round(passage * 1000), ft.AnimationCurve.EASE_IN_OUT))
                await asyncio.sleep(period - 0.1)

        page.run_task(loop)

    def _nav_button(self, route: str, label: str, icon: str) -> ft.Container:
        active = route == self._route

        def on_click(_: ft.ControlEvent) -> None:
            self._navigate(route)

        color = T.TEXT if active else T.TEXT_FAINT
        row = ft.Row(
            [
                lucide_icon(icon, color=color),
                ui_text(
                    label,
                    color=color,
                    weight=ft.FontWeight.W_500,
                    family=T.FONT_UI,
                    expand=True,
                    no_wrap=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        padding = ft.Padding.symmetric(horizontal=8, vertical=10)
        if not active:

            def on_hover(e: ft.ControlEvent) -> None:
                hovered = str(e.data).lower() == "true"
                e.control.bgcolor = T.SELECTED if hovered else None
                tone = T.TEXT_MUTED if hovered else T.TEXT_FAINT
                for part in row.controls:
                    part.color = tone
                e.control.update()

            return ft.Container(
                content=row,
                border_radius=T.RADIUS,
                padding=padding,
                on_click=on_click,
                on_hover=on_hover,
            )

        # Активный пункт: кегль тот же, плашка с обводкой по контуру и бегущий блик (docs Factiosi UMBRAE.md).
        sheen = ft.Container(
            width=80,
            top=0,
            bottom=0,
            left=-96,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT,
                end=ft.Alignment.CENTER_RIGHT,
                colors=["#00ffffff", T.RAIL_SHEEN, "#00ffffff"],
            ),
        )
        self._rail_sheen = sheen
        return ft.Container(
            content=ft.Stack([sheen, ft.Container(content=row, padding=padding)]),
            bgcolor=T.RAIL_ACTIVE_BG,
            border=ft.Border.all(1, T.RAIL_ACTIVE_EDGE),
            border_radius=T.RADIUS,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            on_click=on_click,
        )

    def _build_sidebar(self) -> ft.Container:
        self._rail_sheen = None
        nav = build_nav_items()
        self._nav_controls = [self._nav_button(route, label, icon) for route, label, icon in nav]
        settings_btn = self._nav_button("settings", "Настройки", "settings")
        return ft.Container(
            width=T.SIDEBAR_WIDTH,
            bgcolor=T.GROUND,
            padding=T.RAIL_EDGE,
            border=ft.Border.only(right=ft.BorderSide(1, T.BORDER)),
            content=ft.Column(
                [
                    ft.Column(self._nav_controls, spacing=T.RAIL_ITEM_GAP, tight=True),
                    ft.Container(expand=True),
                    settings_btn,
                ],
                spacing=T.RAIL_ITEM_GAP,
                expand=True,
            ),
        )

    def _build_layout(self) -> None:
        sidebar = self._build_sidebar()
        header = ft.Container(
            content=self._title,
            bgcolor=T.GROUND,
            padding=ft.Padding.only(left=28, right=28, top=20, bottom=12),
        )

        self.page.add(
            ft.Container(
                expand=True,
                bgcolor=T.GROUND,
                content=ft.Row(
                    [
                        sidebar,
                        ft.Column(
                            [
                                header,
                                ft.Container(
                                    content=self._body,
                                    expand=True,
                                    bgcolor=T.GROUND,
                                    padding=ft.Padding.only(left=28, top=8, bottom=8),
                                ),
                            ],
                            expand=True,
                            spacing=0,
                        ),
                    ],
                    expand=True,
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            )
        )

    def _refresh_nav(self) -> None:
        sidebar = self._build_sidebar()
        root = self.page.controls[0]
        if isinstance(root, ft.Container) and isinstance(root.content, ft.Row):
            root.content.controls[0] = sidebar

    def _route_index(self, route: str) -> int:
        nav = build_nav_items()
        for i, (rid, *_rest) in enumerate(nav):
            if rid == route:
                return i
        return 0

    def _navigate(self, route: str) -> None:
        close_active_select(refresh=False)
        if self._home_page:
            self._home_page.stop()
            self._home_page = None
        if self._strategies_page:
            self._strategies_page.stop()
            self._strategies_page = None

        self._route = route
        self.page._tigo_route = route  # type: ignore[attr-defined]
        self.page._tigo_nav_index = self._route_index(route)  # type: ignore[attr-defined]
        self._refresh_nav()

        titles = {rid: label for rid, label, *_ in build_nav_items()}
        titles["settings"] = "Настройки"
        self._title.value = titles.get(route, route)

        self._body.opacity = 0
        self._body.offset = ft.Offset(0, 0.015)
        self.page.update()

        if route == "home":
            self._home_page = HomePage(
                self.page,
                on_strategies_available=self._reload_shell,
            )
            self._body.content = self._home_page.build()
        elif route == "strategies":
            if not has_flowseal_strategies():
                self._navigate("home")
                return
            self._strategies_page = StrategiesPage(self.page)
            self._body.content = self._strategies_page.build()
        elif route == "lists":
            self._body.content = ListsPage(self.page).build()
        elif route == "dns":
            self._body.content = DnsPage(self.page).build()
        elif route == "hosts":
            self._body.content = HostsPage(self.page).build()
        elif route == "tg_ws_proxy":
            self._body.content = TgWsProxyPage(self.page).build()
        elif route == "settings":
            self._body.content = SettingsPage(
                self.page,
                on_theme_change=self._reload_theme,
                on_settings_change=self._reload_shell,
            ).build()
        else:
            self._body.content = ft.Text("Страница не найдена")

        self._body.opacity = 1
        self._body.offset = ft.Offset(0, 0)
        self.page.update()
        if route == "home" and self._home_page:
            self._home_page.on_mounted()

    def _reload_shell(self) -> None:
        route = getattr(self.page, "_tigo_route", self._route)
        settings = get_settings()
        if settings.strategy_source == "custom" and route in ("strategies", "lists"):
            route = "home"
        if route == "strategies" and not has_flowseal_strategies(settings):
            route = "home"
        self.page.controls.clear()
        saved_route = route
        self.show(initial_index=self._route_index(route))
        if saved_route == "settings":
            self._navigate(saved_route)

    def _reload_theme(self) -> None:
        if self._home_page:
            self._home_page.stop()
            self._home_page = None
        if self._strategies_page:
            self._strategies_page.stop()
            self._strategies_page = None
        route = self._route
        self.page.controls.clear()
        app = TigoApp(self.page)
        app.show(initial_index=self._route_index(route))
        if route == "settings":
            app._navigate("settings")


def main(page: ft.Page) -> None:
    TigoApp(page).show()
    if not should_start_hidden():
        page.window.minimized = False
        page.window.visible = True
        page.update()


__all__ = ["TigoApp", "build_nav_items", "main"]
