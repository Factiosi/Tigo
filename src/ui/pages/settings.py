"""Settings page."""

from __future__ import annotations

import threading

import flet as ft

from src.core.paths import APP_NAME, default_app_data_root
from src.core.version import __version__
from src.core.settings import get_settings, save_settings
from src.kernel.public import get_effective_runtime_status, restart_if_running
from src.modules.lifecycle.public import apply_autostart_setting
from src.modules.storage.migrate import apply_storage_root, current_storage_display
from src.modules.strategies.repository import (
    apply_version_retention,
    flowseal_version_select_options,
    list_strategies,
    purge_stale_versions,
    set_active_version,
)
from src.modules.updates.app import check_and_install_app, check_app_only
from src.modules.updates.github import check_for_update
from src.modules.updates.service import (
    MSG_DOWNLOADING,
    MSG_STALE_REMOVED,
    check_and_apply,
    check_only,
)
from src.theme import PORTAL_HUE_OPTIONS, T, apply_theme
from src.ui.components import (
    bind_select_dismiss,
    block_section,
    make_select,
    make_text_field,
    pill_button,
    scroll_page,
    set_pill_disabled,
    ui_text,
    _pill_style,
)
from src.ui.notifications import present_app_update_result, show_toast
from src.ui.probe_table import factiosi_spinner
from src.ui.windows.debug_console import open_debug_console


class SettingsPage:
    def __init__(self, page: ft.Page, on_theme_change, on_settings_change) -> None:
        self.page = page
        self._on_theme_change = on_theme_change
        self._on_settings_change = on_settings_change
        self._storage_field_ref = ft.Ref[ft.TextField]()
        self._storage_apply_btn: ft.FilledButton | None = None
        self._saved_storage_path = current_storage_display()
        self._file_picker = ft.FilePicker()
        self._version_select: ft.Control | None = None
        self._flowseal_check_btn: ft.Control | None = None
        self._flowseal_apply_btn: ft.Control | None = None
        self._tigo_check_btn: ft.Control | None = None
        self._tigo_install_btn: ft.Control | None = None
        self._update_buttons: dict[str, tuple[ft.Control, ft.ProgressRing]] = {}
        self._updates_busy = False
        if self._file_picker not in self.page.services:
            self.page.services.append(self._file_picker)

    @property
    def _storage_field(self) -> ft.TextField | None:
        return self._storage_field_ref.current

    def build(self) -> ft.Control:
        settings = get_settings()
        is_flowseal = settings.strategy_source == "flowseal"
        self._saved_storage_path = current_storage_display()

        theme_select = make_select(
            self.page,
            "Тема оформления",
            [
                ("dark", "Тёмная"),
                ("light", "Светлая"),
            ],
            settings.theme_mode,
            on_change=self._on_theme_mode_change,
        )
        hue_select = make_select(
            self.page,
            "Цветовая схема",
            PORTAL_HUE_OPTIONS,
            settings.portal_hue,
            on_change=self._on_portal_hue_change,
        )

        autostart_cb = ft.Checkbox(
            label="Добавить в автозапуск",
            value=settings.autostart_enabled,
            label_style=ft.TextStyle(font_family=T.FONT_FAMILY, color=T.TEXT),
            on_change=bind_select_dismiss(
                lambda e: self._on_bool_setting("autostart_enabled", bool(e.control.value), autostart=True)
            ),
        )
        launch_last_cb = ft.Checkbox(
            label="Запускать последнюю активную стратегию вместе с запуском программы",
            value=settings.launch_last_strategy_on_startup,
            label_style=ft.TextStyle(font_family=T.FONT_FAMILY, color=T.TEXT),
            on_change=bind_select_dismiss(
                lambda e: self._on_bool_setting("launch_last_strategy_on_startup", bool(e.control.value))
            ),
        )
        start_tray_cb = ft.Checkbox(
            label="Запускать в свёрнутом виде (в трее)",
            value=settings.start_minimized_to_tray,
            label_style=ft.TextStyle(font_family=T.FONT_FAMILY, color=T.TEXT),
            on_change=bind_select_dismiss(
                lambda e: self._on_bool_setting("start_minimized_to_tray", bool(e.control.value))
            ),
        )
        close_select = make_select(
            self.page,
            "Реакция на кнопку закрытия (крестик)",
            [
                ("exit", "Закрыть программу"),
                ("minimize_tray", "Свернуть в трей"),
            ],
            settings.close_action,
            on_change=lambda v: self._on_close_action_change(v),
        )

        source_select = make_select(
            self.page,
            "Источник стратегий",
            [
                ("flowseal", "Стратегии Flowseal"),
                ("custom", "Своя стратегия"),
            ],
            settings.strategy_source,
            on_change=self._on_strategy_source_change,
        )

        sections: list[ft.Control] = [
            block_section("Оформление", theme_select, hue_select),
            block_section(
                "Поведение",
                autostart_cb,
                launch_last_cb,
                start_tray_cb,
                close_select,
            ),
            block_section("Стратегии", source_select),
        ]

        if is_flowseal:
            auto_check_cb = ft.Checkbox(
                label="Автоматически проверять обновления при запуске",
                value=settings.auto_check_updates_on_startup,
                label_style=ft.TextStyle(font_family=T.FONT_FAMILY, color=T.TEXT),
                on_change=bind_select_dismiss(
                    lambda e: self._on_bool_setting("auto_check_updates_on_startup", bool(e.control.value))
                ),
            )
            auto_apply_cb = ft.Checkbox(
                label="Автоматически скачивать обновления и применять",
                value=settings.auto_promote_updates,
                label_style=ft.TextStyle(font_family=T.FONT_FAMILY, color=T.TEXT),
                on_change=bind_select_dismiss(
                    lambda e: self._on_bool_setting("auto_promote_updates", bool(e.control.value))
                ),
            )
            versions = flowseal_version_select_options(settings)
            version_options = versions
            self._version_select = make_select(
                self.page,
                "Версия flowseal",
                version_options,
                settings.active_version or "",
                on_change=self._on_version_change,
            )
            self._update_buttons.clear()
            self._flowseal_check_btn = self._update_action_button(
                "flowseal:check",
                "Проверить обновления",
                on_click=self._check_updates_only,
            )
            self._flowseal_apply_btn = self._update_action_button(
                "flowseal:apply",
                "Проверить обновления и применить",
                primary=True,
                on_click=self._check_and_apply,
            )
            sections.append(
                block_section(
                    "Обновление стратегий Flowseal",
                    auto_check_cb,
                    auto_apply_cb,
                    self._version_select,
                    ft.Row(
                        [self._flowseal_check_btn, self._flowseal_apply_btn],
                        wrap=True,
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

            retention_select = make_select(
                self.page,
                "Хранение версий стратегий",
                [
                    ("all", "Хранить все версии"),
                    ("latest_only", "Хранить только актуальную версию"),
                    ("keep_previous", "Хранить актуальную и предыдущую"),
                ],
                settings.version_retention,
                on_change=self._on_retention_change,
            )
            purge_btn = pill_button(
                "Удалить неактуальные версии (принудительно)",
                destructive=True,
                on_click=self._purge_versions,
            )
            sections.append(block_section("Flowseal", retention_select, purge_btn))

        storage_input = make_text_field(
            "Путь хранения данных",
            self._saved_storage_path,
            on_change=self._on_storage_field_change,
            field_ref=self._storage_field_ref,
        )
        browse_btn = pill_button("Выбрать папку", on_click=self._pick_folder)
        self._storage_apply_btn = pill_button(
            "Применить",
            primary=True,
            on_click=self._apply_storage,
        )
        set_pill_disabled(self._storage_apply_btn, True)

        sections.extend(
            [
                block_section(
                    "Место хранения",
                    ui_text(
                        f"По умолчанию: {default_app_data_root()}",
                        size=12,
                        color=T.TEXT_MUTED,
                    ),
                    ft.Row(
                        [storage_input, browse_btn],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    self._storage_apply_btn,
                ),
                block_section(
                    "Консоль",
                    ui_text(
                        "Консоль отладки пишет все действия приложения подробно. "
                        "Записи старше 1 часа удаляются автоматически.",
                        size=12,
                        color=T.TEXT_MUTED,
                    ),
                    pill_button("Открыть консоль отладки", on_click=self._open_console),
                ),
            ]
        )

        app_auto_check_cb = ft.Checkbox(
            label="Автоматически проверять обновления при запуске",
            value=settings.auto_check_app_updates_on_startup,
            label_style=ft.TextStyle(font_family=T.FONT_FAMILY, color=T.TEXT),
            on_change=bind_select_dismiss(
                lambda e: self._on_bool_setting(
                    "auto_check_app_updates_on_startup",
                    bool(e.control.value),
                )
            ),
        )
        app_auto_install_cb = ft.Checkbox(
            label="Автоматически скачивать обновления и устанавливать",
            value=settings.auto_install_app_updates,
            label_style=ft.TextStyle(font_family=T.FONT_FAMILY, color=T.TEXT),
            on_change=bind_select_dismiss(
                lambda e: self._on_bool_setting(
                    "auto_install_app_updates",
                    bool(e.control.value),
                )
            ),
        )
        self._tigo_check_btn = self._update_action_button(
            "tigo:check",
            "Проверить обновления",
            on_click=self._check_app_updates_only,
        )
        self._tigo_install_btn = self._update_action_button(
            "tigo:install",
            "Проверить обновления и установить",
            primary=True,
            on_click=self._check_and_install_app_updates,
        )
        sections.append(
            block_section(
                "Обновления Tigo",
                ui_text(f"{APP_NAME} v{__version__}", size=12, color=T.TEXT_MUTED),
                app_auto_check_cb,
                app_auto_install_cb,
                ft.Row(
                    [self._tigo_check_btn, self._tigo_install_btn],
                    wrap=True,
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        )

        return scroll_page(
            *sections,
            page=self.page,
        )

    def _update_action_button(
        self,
        role: str,
        text: str,
        *,
        primary: bool = False,
        on_click,
    ) -> ft.Control:
        spinner = factiosi_spinner(size=14)
        if primary:
            spinner.color = T.ON_ACCENT
            spinner.bgcolor = T.ACCENT_DIM
        spinner.visible = False
        label = ft.Text(
            text,
            size=T.FONT_BODY,
            font_family=T.FONT_FAMILY,
            color=T.ON_ACCENT if primary else T.ACCENT,
        )
        content = ft.Row(
            [spinner, label],
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        style = _pill_style(primary=primary)
        wrapped = bind_select_dismiss(on_click)
        btn_cls = ft.FilledButton if primary else ft.OutlinedButton
        btn = btn_cls(
            content=content,
            height=T.FIELD_HEIGHT,
            style=style,
            on_click=wrapped,
            disabled=self._updates_busy,
        )
        self._update_buttons[role] = (btn, spinner)
        return btn

    def _set_updates_loading(self, loading: bool, *, active: str | None = None) -> None:
        self._updates_busy = loading
        for role, (btn, spinner) in self._update_buttons.items():
            spinner.visible = loading and role == active
            btn.disabled = loading
        if self.page:
            try:
                self.page.update()
            except RuntimeError:
                pass

    def _run_updates_bg(self, work, on_done, *, active: str) -> None:
        if self._updates_busy:
            return
        self._set_updates_loading(True, active=active)

        def runner() -> None:
            try:
                if active == "flowseal:apply":
                    info = check_for_update(get_settings().active_version)
                    if info.update_available:
                        self._ui(
                            lambda: show_toast(
                                self.page,
                                MSG_DOWNLOADING,
                                kind="warning",
                                duration=6.0,
                            )
                        )
                result = work()
            except Exception as exc:  # noqa: BLE001
                result = exc

            def finish() -> None:
                self._set_updates_loading(False)
                on_done(result)

            try:
                self.page.run_thread(finish)
            except AttributeError:
                finish()

        threading.Thread(target=runner, daemon=True).start()

    def _ui(self, fn) -> None:
        try:
            self.page.run_thread(fn)
        except AttributeError:
            fn()

    def _check_updates_only(self, _: ft.ControlEvent) -> None:
        def work():
            return check_only()

        def done(result):
            ok, msg, kind = result
            show_toast(self.page, msg, kind=kind if ok else "error")

        self._run_updates_bg(work, done, active="flowseal:check")

    def _check_and_apply(self, _: ft.ControlEvent) -> None:
        def work():
            return check_and_apply()

        def done(result):
            if isinstance(result, Exception):
                show_toast(self.page, str(result), kind="error")
                return
            show_toast(self.page, result.message, kind=result.toast_kind)
            if result.ok and result.version_changed:
                self._on_settings_change()

        self._run_updates_bg(work, done, active="flowseal:apply")

    def _check_app_updates_only(self, _: ft.ControlEvent) -> None:
        def work():
            return check_app_only()

        def done(result):
            ok, msg, kind = result
            present_app_update_result(self.page, ok, msg, kind)

        self._run_updates_bg(work, done, active="tigo:check")

    def _check_and_install_app_updates(self, _: ft.ControlEvent) -> None:
        def work():
            return check_and_install_app()

        def done(result):
            ok, msg, kind = result
            if ok and kind == "success":
                return
            show_toast(self.page, msg, kind=kind if ok else "error")

        self._run_updates_bg(work, done, active="tigo:install")

    def _on_version_change(self, version: str) -> None:
        if not version:
            return
        set_active_version(version)
        strategies = list_strategies()
        settings = get_settings()
        known = {s.id for s in strategies}
        if settings.selected_strategy not in known:
            settings.selected_strategy = strategies[0].id if strategies else ""
            save_settings(settings)
        if get_effective_runtime_status().running:
            ok, msg = restart_if_running()
            self._snack(msg or f"Версия {version}. Перезапущено.", error=not ok)
        else:
            self._snack(f"Версия flowseal: {version}.")

    def _on_bool_setting(self, field: str, value: bool, *, autostart: bool = False) -> None:
        settings = get_settings()
        setattr(settings, field, value)
        save_settings(settings)
        if autostart:
            ok, msg = apply_autostart_setting(value)
            if not ok and msg:
                self._snack(msg, error=True)

    def _on_close_action_change(self, value: str) -> None:
        settings = get_settings()
        settings.close_action = value  # type: ignore[assignment]
        save_settings(settings)

    def _on_theme_mode_change(self, mode: str) -> None:
        settings = get_settings()
        settings.theme_mode = mode  # type: ignore[assignment]
        save_settings(settings)
        apply_theme(mode, settings.portal_hue)  # type: ignore[arg-type]
        self._on_theme_change()

    def _on_portal_hue_change(self, hue: str) -> None:
        settings = get_settings()
        settings.portal_hue = hue  # type: ignore[assignment]
        save_settings(settings)
        apply_theme(settings.theme_mode, hue)  # type: ignore[arg-type]
        self._on_theme_change()

    def _on_strategy_source_change(self, value: str) -> None:
        settings = get_settings()
        settings.strategy_source = value  # type: ignore[assignment]
        save_settings(settings)
        self._on_settings_change()

    def _on_retention_change(self, value: str) -> None:
        settings = get_settings()
        settings.version_retention = value  # type: ignore[assignment]
        if value == "keep_previous":
            settings.keep_version_count = 2
        save_settings(settings)
        removed = apply_version_retention()
        if removed:
            show_toast(self.page, MSG_STALE_REMOVED, kind="info")

    def _on_storage_field_change(self, e: ft.ControlEvent) -> None:
        self._update_storage_apply_state()

    def _update_storage_apply_state(self) -> None:
        if not self._storage_apply_btn or not self._storage_field:
            return
        dirty = (self._storage_field.value or "").strip() != self._saved_storage_path
        set_pill_disabled(self._storage_apply_btn, not dirty)
        if not dirty:
            self._storage_apply_btn.text = "Применить"
        self.page.update()

    def _pick_folder(self, _: ft.ControlEvent) -> None:
        async def pick() -> None:
            path = await self._file_picker.get_directory_path(
                dialog_title=f"Выберите папку для данных {APP_NAME}",
            )
            if path and self._storage_field:
                self._storage_field.value = path
                self._update_storage_apply_state()

        self.page.run_task(pick)

    def _apply_storage(self, _: ft.ControlEvent) -> None:
        if not self._storage_field:
            return
        path = self._storage_field.value or ""

        def work():
            return apply_storage_root(path)

        def done(result):
            ok, msg = result
            if ok:
                self._saved_storage_path = current_storage_display()
                if self._storage_field:
                    self._storage_field.value = self._saved_storage_path
                if self._storage_apply_btn:
                    self._storage_apply_btn.text = "Применено"
                    set_pill_disabled(self._storage_apply_btn, True)
            self._snack(msg, error=not ok)

        def runner():
            result = work()
            try:
                self.page.run_thread(lambda: done(result))
            except AttributeError:
                done(result)

        threading.Thread(target=runner, daemon=True).start()

    def _purge_versions(self, _: ft.ControlEvent) -> None:
        def work():
            return purge_stale_versions(keep=1)

        def done(removed):
            if removed:
                show_toast(self.page, MSG_STALE_REMOVED, kind="info")
            else:
                show_toast(self.page, "Нет версий для удаления.", kind="info")

        def runner():
            result = work()
            try:
                self.page.run_thread(lambda: done(result))
            except AttributeError:
                done(result)

        threading.Thread(target=runner, daemon=True).start()

    def _open_console(self, _: ft.ControlEvent) -> None:
        ok, message = open_debug_console()
        self._snack(message, error=not ok)

    def _toast(self, message: str, *, kind: str = "info", error: bool = False) -> None:
        show_toast(self.page, message, kind="error" if error else kind)

    def _snack(self, message: str, *, error: bool = False) -> None:
        self._toast(message, error=error)
