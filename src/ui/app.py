"""Tigo application shell."""

from __future__ import annotations

import flet as ft

from src.core.branding import app_window_icon_path
from src.core.events import subscribe, unsubscribe
from src.core.fonts import register_mono_font
from src.core.paths import APP_NAME
from src.core.version import __version__
from src.core.settings import get_settings, save_settings
from src.modules.strategies.repository import has_flowseal_strategies
from src.theme import T, apply_theme, build_flet_theme, build_theme_tokens
from src.modules.lifecycle.public import handle_window_close, should_start_hidden
from src.ui.components import ANIM, close_active_select, ui_text
from src.ui.pages.dns import DnsPage
from src.ui.pages.home import HomePage
from src.ui.pages.lists import ListsPage
from src.ui.pages.strategies import StrategiesPage
from src.ui.pages.settings import SettingsPage


def build_nav_items() -> list[tuple[str, str, str, str]]:
    settings = get_settings()
    items: list[tuple[str, str, str, str]] = [
        ("home", "Главный экран", ft.Icons.HOME_OUTLINED, ft.Icons.HOME_ROUNDED),
    ]
    if settings.strategy_source == "flowseal":
        if has_flowseal_strategies(settings):
            items.append(
                ("strategies", "Подбор стратегий", ft.Icons.TUNE_OUTLINED, ft.Icons.TUNE),
            )
        items.append(
            ("lists", "Редактирование листов", ft.Icons.EDIT_NOTE_OUTLINED, ft.Icons.EDIT_NOTE),
        )
    items.extend(
        [
            ("dns", "Изменение DNS", ft.Icons.DNS_OUTLINED, ft.Icons.DNS),
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

    def _on_strategies_changed(self) -> None:
        if not self.page:
            return
        try:
            self.page.run_thread(self._reload_shell)
        except AttributeError:
            self._reload_shell()

    def _reset_shell(self) -> None:
        self._body = ft.Container(expand=True, bgcolor=T.GROUND, animate_opacity=ANIM)
        self._title = ui_text("", size=T.FONT_TITLE, weight=ft.FontWeight.W_600)
        self._home_page = None
        self._strategies_page = None

    def show(self, *, initial_index: int = 0) -> None:
        settings = get_settings()
        apply_theme(settings.theme_mode, settings.portal_hue)
        self._reset_shell()
        self._configure_page()
        nav = build_nav_items()
        if 0 <= initial_index < len(nav):
            self._route = nav[initial_index][0]
        elif initial_index >= len(nav):
            self._route = "settings"
        self._build_layout()
        unsubscribe("strategies_changed", self._strategies_changed_handler)
        subscribe("strategies_changed", self._strategies_changed_handler)
        self._navigate(self._route)

    def _configure_page(self) -> None:
        page = self.page
        settings = get_settings()
        register_mono_font(page)
        page.title = APP_NAME
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

    def _nav_button(self, route: str, label: str, icon, selected_icon) -> ft.Container:
        active = route == self._route

        def on_click(_: ft.ControlEvent) -> None:
            self._navigate(route)

        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(selected_icon if active else icon, color=T.ACCENT if active else T.TEXT_MUTED, size=20),
                    ui_text(
                        label,
                        color=T.ACCENT if active else T.TEXT,
                        weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400,
                        expand=True,
                    ),
                ],
                spacing=12,
            ),
            bgcolor=T.ACCENT_SOFT if active else None,
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            on_click=on_click,
            ink=not active,
            ink_color=T.ACCENT_SOFT,
        )

    def _build_sidebar(self) -> ft.Container:
        nav = build_nav_items()
        self._nav_controls = [
            self._nav_button(route, label, icon, selected_icon)
            for route, label, icon, selected_icon in nav
        ]
        settings_btn = self._nav_button(
            "settings",
            "Настройки",
            ft.Icons.SETTINGS_OUTLINED,
            ft.Icons.SETTINGS,
        )

        return ft.Container(
            width=T.SIDEBAR_WIDTH,
            bgcolor=T.GROUND,
            padding=ft.Padding.only(left=12, right=12, top=16, bottom=16),
            content=ft.Column(
                [
                    ft.Column(self._nav_controls, spacing=4, tight=True),
                    ft.Container(expand=True),
                    settings_btn,
                ],
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
        self.page._z1ui_route = route  # type: ignore[attr-defined]
        self.page._z1ui_nav_index = self._route_index(route)  # type: ignore[attr-defined]
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
        route = getattr(self.page, "_z1ui_route", self._route)
        settings = get_settings()
        if settings.strategy_source == "custom" and route in ("strategies", "lists"):
            route = "home"
        if route == "strategies" and not has_flowseal_strategies(settings):
            route = "home"
        self.page.controls.clear()
        saved_route = route
        self.show(initial_index=self._route_index(route))
        if saved_route == "settings":
            self._navigate("settings")

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


__all__ = ["TigoApp", "build_nav_items", "main"]
