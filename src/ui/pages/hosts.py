"""Hosts editor page."""

from __future__ import annotations

import threading

import flet as ft

from src.modules.hosts.hosts_file import hosts_path
from src.modules.hosts.service import (
    HostsState,
    load_state,
    open_in_editor,
    restore_backup,
    restore_default,
    set_preset,
)
from src.ui.components import block_section, pill_button, scroll_page, status_pill, ui_text
from src.ui.notifications import show_toast
from src.ui.theme import T


class HostsPage:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self._busy = False
        self._root = ft.Container()

    def build(self) -> ft.Control:
        self._render(load_state())
        return self._root

    # rendering -----------------------------------------------------------------
    def _render(self, state: HostsState) -> None:
        preset_rows = [self._preset_row(preset, count) for preset, count in state.presets]
        tigo_entries = sum(state.summary.blocks.values())
        file_info = ui_text(
            f"{hosts_path()} · записей: {state.summary.entries}, из них Tigo: {tigo_entries}",
            color=T.TEXT_MUTED,
            size=12,
            selectable=True,
        )
        self._root.content = scroll_page(
            block_section("Готовые наборы", *preset_rows),
            block_section(
                "Файл hosts",
                file_info,
                ft.Row(
                    [
                        pill_button("Открыть в редакторе", on_click=self._open),
                        pill_button("Обновить", on_click=lambda _: self._reload()),
                        pill_button(
                            "Вернуть копию до Tigo",
                            on_click=self._restore_backup,
                            disabled=not state.has_backup,
                        ),
                        pill_button("Стандартный hosts Windows", destructive=True, on_click=self._restore_default),
                    ],
                    spacing=8,
                    wrap=True,
                ),
            ),
            page=self.page,
        )

    def _preset_row(self, preset, count: int) -> ft.Control:
        enabled = count > 0
        badge = status_pill("active", f"Включено · {count}") if enabled else status_pill("offline", "Выключено")
        return ft.Row(
            [
                ft.Column(
                    [
                        ui_text(preset.title, weight=ft.FontWeight.W_500),
                        ui_text(preset.description, color=T.TEXT_MUTED, size=12),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
                badge,
                pill_button(
                    "Выключить" if enabled else "Включить",
                    primary=not enabled,
                    on_click=lambda _, pid=preset.id, on=not enabled: self._run(lambda: set_preset(pid, on)),
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _reload(self) -> None:
        self._render(load_state())
        self.page.update()

    # actions -------------------------------------------------------------------
    def _run(self, work) -> None:
        if self._busy:
            return
        self._busy = True

        def runner() -> None:
            try:
                ok, message = work()
            except Exception as exc:  # noqa: BLE001
                ok, message = False, str(exc)

            def finish() -> None:
                self._busy = False
                self._reload()
                show_toast(self.page, message, kind="success" if ok else "error")

            try:
                self.page.run_thread(finish)
            except AttributeError:
                finish()

        threading.Thread(target=runner, daemon=True).start()

    def _open(self, _: ft.ControlEvent) -> None:
        ok, message = open_in_editor()
        show_toast(self.page, message, kind="success" if ok else "error")

    def _restore_backup(self, _: ft.ControlEvent) -> None:
        self._run(restore_backup)

    def _restore_default(self, _: ft.ControlEvent) -> None:
        self._run(restore_default)
