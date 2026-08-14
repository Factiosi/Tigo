"""Factiosi UI helpers for Tigo."""

from __future__ import annotations

import math
from typing import Callable

import flet as ft

from src.theme import T

ANIM = ft.Animation(280, ft.AnimationCurve.EASE_OUT_CUBIC)
ANIM_FAST = ft.Animation(160, ft.AnimationCurve.EASE_OUT)
CHEVRON_ANIM = ft.Animation(180, ft.AnimationCurve.EASE_OUT)
EXPAND_ANIM = ft.Animation(220, ft.AnimationCurve.EASE_OUT_CUBIC)

MENU_MAX_HEIGHT = 280
MENU_ITEM_HEIGHT = 40
MENU_EDGE_INSET = 4
MENU_POPUP_VPAD = 8
MENU_ITEM_RADIUS = 6
MENU_SHADOW = ft.BoxShadow(
    blur_radius=24,
    color="#00000080",
    offset=ft.Offset(0, 8),
)
BUTTON_HEIGHT = T.FIELD_HEIGHT
LOG_PANEL_HEIGHT_HOME = 280
LOG_PANEL_HEIGHT_TEST = 560

_active_select_close: Callable[[], None] | None = None
_page_keyboard_saved: Callable[[ft.KeyboardEvent], None] | None = None
_select_scroll_reposition: Callable[[float], None] | None = None
MENU_GAP = 8


def _select_menu_item_style(*, selected: bool) -> ft.ButtonStyle:
    hover_bg = T.OVERLAY_HOVER
    text_color = T.MENU_SELECTED if selected else T.TEXT
    return ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=MENU_ITEM_RADIUS),
        padding=ft.Padding.symmetric(horizontal=12, vertical=0),
        alignment=ft.Alignment(-1, 0),
        color={ft.ControlState.DEFAULT: text_color},
        text_style=ft.TextStyle(
            size=T.FONT_BODY,
            font_family=T.FONT_FAMILY,
            weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
        ),
        bgcolor={
            ft.ControlState.HOVERED: hover_bg,
            ft.ControlState.FOCUSED: hover_bg,
        },
        overlay_color={
            ft.ControlState.HOVERED: hover_bg,
            ft.ControlState.FOCUSED: hover_bg,
        },
        mouse_cursor=ft.MouseCursor.CLICK,
        visual_density=ft.VisualDensity.COMPACT,
    )


def _raise_menu_overlay(page: ft.Page, menu_popup: ft.Control) -> None:
    """Keep the open menu last in page.overlay to win z-order."""
    if menu_popup in page.overlay:
        page.overlay.remove(menu_popup)
    page.overlay.append(menu_popup)


def _close_active_select(*, refresh: bool = True) -> None:
    global _active_select_close
    if _active_select_close is not None:
        close = _active_select_close
        _active_select_close = None
        close(refresh=refresh)


def close_active_select(*, refresh: bool = True) -> None:
    """Close the currently open custom select, if any."""
    _close_active_select(refresh=refresh)


def _global_keyboard_handler(e: ft.KeyboardEvent) -> None:
    if e.key == "Escape" and _active_select_close is not None:
        _active_select_close()
        return
    saved = _page_keyboard_saved
    if saved is not None and saved is not _global_keyboard_handler:
        saved(e)


def _attach_page_keyboard(page: ft.Page) -> None:
    global _page_keyboard_saved
    if _page_keyboard_saved is None:
        _page_keyboard_saved = page.on_keyboard_event  # type: ignore[assignment]
        page.on_keyboard_event = _global_keyboard_handler


def _detach_page_keyboard(page: ft.Page) -> None:
    global _page_keyboard_saved
    if _active_select_close is None and _page_keyboard_saved is not None:
        page.on_keyboard_event = _page_keyboard_saved  # type: ignore[assignment]
        _page_keyboard_saved = None


def _calc_menu_content_height(option_count: int) -> int:
    if option_count <= 0:
        return MENU_ITEM_HEIGHT
    spacing = max(0, option_count - 1) * 2
    inner = option_count * MENU_ITEM_HEIGHT + spacing
    return min(MENU_MAX_HEIGHT - MENU_POPUP_VPAD, inner)


def _calc_menu_height(option_count: int) -> int:
    return _calc_menu_content_height(option_count) + MENU_POPUP_VPAD


def _window_height(page: ft.Page) -> float:
    window = getattr(page, "window", None)
    if window is not None and window.height:
        return float(window.height)
    if page.height:
        return float(page.height)
    return 760.0


def _content_bottom(page: ft.Page) -> float:
    """Bottom edge of the scrollable body (window coords), excluding body padding."""
    return _window_height(page) - 8.0


def _global_from_tap(e: ft.TapEvent) -> tuple[float, float] | None:
    if e.global_position is None or e.local_position is None:
        return None
    field_left = e.global_position.x - e.local_position.x
    field_top = e.global_position.y - e.local_position.y
    return field_left, field_top


def _menu_height_for_options(option_count: int, resolved: int | None) -> float:
    if resolved is not None:
        return float(resolved)
    return float(_calc_menu_height(option_count))


def _placement_menu_height(option_count: int, resolved: int | None) -> float:
    """Height used for flip/placement (always known, even for short lists)."""
    return _menu_height_for_options(option_count, resolved or _calc_menu_height(option_count))


def _should_open_upward(
    field_top: float,
    menu_height: float,
    content_bottom: float,
) -> bool:
    space_below = content_bottom - (field_top + T.FIELD_HEIGHT + MENU_GAP)
    space_above = field_top - MENU_GAP
    if space_below >= menu_height:
        return False
    if space_above >= menu_height:
        return True
    return space_above > space_below


def _pill_style(*, primary: bool = False, destructive: bool = False) -> ft.ButtonStyle:
    shape = ft.RoundedRectangleBorder(radius=99)
    text_style = ft.TextStyle(size=T.FONT_BODY, font_family=T.FONT_FAMILY)
    padding = ft.Padding.symmetric(horizontal=16, vertical=0)
    hover_overlay = T.ACCENT_SOFT
    disabled_bg = T.ELEVATED
    disabled_fg = T.TEXT_MUTED
    disabled_side = T.BORDER
    if destructive:
        return ft.ButtonStyle(
            color={
                ft.ControlState.DEFAULT: T.STATUS_ERROR,
                ft.ControlState.DISABLED: disabled_fg,
            },
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(1, T.STATUS_ERROR),
                ft.ControlState.DISABLED: ft.BorderSide(1, disabled_side),
            },
            bgcolor={
                ft.ControlState.DISABLED: disabled_bg,
            },
            shape=shape,
            padding=padding,
            text_style=text_style,
            elevation=0,
            overlay_color={
                ft.ControlState.HOVERED: T.STATUS_ERROR_BG,
                ft.ControlState.PRESSED: T.STATUS_ERROR_BG,
            },
        )
    if primary:
        return ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: T.ACCENT,
                ft.ControlState.DISABLED: disabled_bg,
            },
            color={
                ft.ControlState.DEFAULT: T.ON_ACCENT,
                ft.ControlState.DISABLED: disabled_fg,
            },
            shape=shape,
            padding=padding,
            text_style=text_style,
            elevation=0,
            overlay_color={
                ft.ControlState.HOVERED: T.ACCENT_DIM,
                ft.ControlState.FOCUSED: T.ACCENT_DIM,
                ft.ControlState.PRESSED: T.ACCENT_DIM,
            },
        )
    return ft.ButtonStyle(
        color={
            ft.ControlState.DEFAULT: T.ACCENT,
            ft.ControlState.DISABLED: disabled_fg,
        },
        side={
            ft.ControlState.DEFAULT: ft.BorderSide(1, T.BORDER_STRONG),
            ft.ControlState.DISABLED: ft.BorderSide(1, disabled_side),
        },
        bgcolor={
            ft.ControlState.DISABLED: disabled_bg,
        },
        shape=shape,
        padding=padding,
        text_style=text_style,
        elevation=0,
        overlay_color={
            ft.ControlState.HOVERED: hover_overlay,
            ft.ControlState.FOCUSED: hover_overlay,
            ft.ControlState.PRESSED: hover_overlay,
        },
    )


def ui_text(
    value: str,
    *,
    size: float | None = None,
    color: str | None = None,
    weight: ft.FontWeight | None = None,
    **kwargs,
) -> ft.Text:
    return ft.Text(
        value,
        size=size if size is not None else T.FONT_BODY,
        color=color if color is not None else T.TEXT,
        weight=weight,
        font_family=T.FONT_FAMILY,
        **kwargs,
    )


def status_pill(status: str, label: str | None = None) -> ft.Container:
    colors = {
        "active": (T.STATUS_ACTIVE, T.STATUS_ACTIVE_BG, "Активно"),
        "connecting": (T.STATUS_CONNECTING, T.STATUS_CONNECTING_BG, "Подключение"),
        "expiring": (T.STATUS_EXPIRING, T.STATUS_EXPIRING_BG, "Предупреждение"),
        "error": (T.STATUS_ERROR, T.STATUS_ERROR_BG, "Ошибка"),
        "offline": (T.STATUS_OFFLINE, T.STATUS_OFFLINE_BG, "Отключено"),
    }
    fg, bg, default = colors.get(status, colors["offline"])
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(width=6, height=6, bgcolor=fg, border_radius=99),
                ui_text(label or default, size=12, color=fg, weight=ft.FontWeight.W_500),
            ],
            spacing=6,
            tight=True,
        ),
        bgcolor=bg,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        border_radius=99,
    )


def block_section(title: str | None, *controls: ft.Control) -> ft.Container:
    header: list[ft.Control] = []
    if title:
        header.append(
            ui_text(title, size=T.FONT_LABEL, color=T.TEXT_MUTED, weight=ft.FontWeight.W_500)
        )
    return ft.Container(
        content=ft.Column(
            [
                *header,
                ft.Container(
                    content=ft.Column(
                        list(controls),
                        spacing=T.SPACE_FIELD,
                        tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                    bgcolor=T.SURFACE,
                    border=ft.Border.all(1, T.BORDER),
                    border_radius=T.RADIUS,
                    padding=T.SECTION_PAD,
                ),
            ],
            spacing=8,
            tight=True,
        ),
        animate_opacity=ANIM,
    )


def _register_page_scroll(page: ft.Page, view: ft.ListView) -> None:
    page._tigo_page_scroll = view  # type: ignore[attr-defined]
    page._tigo_page_scroll_offset = 0  # type: ignore[attr-defined]

    def track_scroll(e: ft.OnScrollEvent) -> None:
        page._tigo_page_scroll_offset = e.pixels  # type: ignore[attr-defined]
        if _select_scroll_reposition is not None:
            _select_scroll_reposition(e.pixels)

    view.on_scroll = track_scroll


def scroll_page(*controls: ft.Control, page: ft.Page | None = None) -> ft.ListView:
    def on_background_click(e: ft.ControlEvent) -> None:
        _close_active_select(refresh=False)
        if e.page:
            e.page.update()

    view = ft.ListView(
        controls=[
            ft.Container(
                content=ft.Column(
                    [*controls, ft.Container(height=24)],
                    spacing=T.SPACE_SECTION,
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                padding=ft.Padding.only(right=28),
                on_click=on_background_click,
            )
        ],
        expand=True,
        spacing=0,
        padding=0,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
    if page is not None:
        _register_page_scroll(page, view)
    return view


def set_pill_disabled(btn: ft.Control, disabled: bool) -> None:
    """Update pill button disabled state (Material shows forbidden cursor when disabled)."""
    if isinstance(btn, (ft.FilledButton, ft.OutlinedButton)):
        btn.disabled = disabled


def make_text_field(
    label: str,
    value: str = "",
    *,
    on_change: Callable[[ft.ControlEvent], None] | None = None,
    read_only: bool = False,
    expand: bool = True,
    border_radius: float = 12,
    field_ref: ft.Ref[ft.TextField] | None = None,
) -> ft.Column:
    field = ft.TextField(
        ref=field_ref,
        value=value,
        height=T.FIELD_HEIGHT,
        text_size=T.FONT_BODY,
        text_style=ft.TextStyle(font_family=T.FONT_FAMILY, color=T.TEXT),
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=0),
        border_radius=border_radius,
        filled=True,
        bgcolor=T.ELEVATED,
        border_color=T.BORDER,
        focused_border_color=T.ACCENT,
        cursor_color=T.ACCENT,
        selection_color=T.ACCENT_SOFT,
        expand=expand,
        read_only=read_only,
        on_change=on_change,
        on_focus=lambda _: _close_active_select(refresh=False),
    )
    return ft.Column(
        [
            ui_text(label, size=T.FONT_LABEL, color=T.TEXT_MUTED, weight=ft.FontWeight.W_500),
            field,
        ],
        spacing=T.SPACE_LABEL,
        tight=True,
        expand=expand,
    )


def pill_button(
    text: str,
    *,
    primary: bool = False,
    destructive: bool = False,
    on_click=None,
    disabled: bool = False,
) -> ft.Control:
    style = _pill_style(primary=primary, destructive=destructive)
    if primary:
        return ft.FilledButton(
            text,
            disabled=disabled,
            height=BUTTON_HEIGHT,
            style=style,
            on_click=_wrap_click(on_click),
        )
    return ft.OutlinedButton(
        text,
        disabled=disabled,
        height=BUTTON_HEIGHT,
        style=style,
        on_click=_wrap_click(on_click),
    )


def _wrap_click(handler):
    if handler is None:
        return None

    def wrapped(e: ft.ControlEvent) -> None:
        _close_active_select(refresh=False)
        page = None
        try:
            page = e.page
        except RuntimeError:
            pass
        handler(e)
        if page is not None:
            try:
                page.update()
            except RuntimeError:
                pass

    return wrapped


def bind_select_dismiss(handler):
    """Close an open select, then run the control handler (one page.update at the end)."""
    return _wrap_click(handler)


def make_select(
    page: ft.Page,
    label: str,
    options: list[tuple[str, str]],
    value: str,
    on_change=None,
    *,
    menu_height: int | None = None,
    disabled: bool = False,
    option_trailing: Callable[[str], ft.Control | None] | None = None,
) -> ft.Column:
    if menu_height is not None:
        resolved_menu_height: int = menu_height
    else:
        resolved_menu_height = _calc_menu_height(len(options))
    menu_content_height = max(MENU_ITEM_HEIGHT, resolved_menu_height - MENU_POPUP_VPAD)

    state: dict[str, object] = {"value": value or "", "open": False, "field_width": None}
    chevron_ref = ft.Ref[ft.Icon]()
    field_ref = ft.Ref[ft.Container]()

    selected_label = next((t for k, t in options if k == state["value"]), "")
    value_text = ui_text(
        selected_label or state["value"] or "Выбрать",
        size=T.FONT_BODY,
        color=T.TEXT if selected_label or state["value"] else T.TEXT_FAINT,
        expand=True,
    )

    menu_col = ft.Column(
        spacing=2,
        tight=True,
        scroll=ft.ScrollMode.ADAPTIVE if len(options) > 6 else None,
        height=menu_content_height,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    menu_popup = ft.Container(
        content=menu_col,
        bgcolor=T.OVERLAY,
        border=ft.Border.all(1, T.BORDER),
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=MENU_EDGE_INSET, vertical=4),
        height=resolved_menu_height,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        visible=False,
        opacity=0,
        scale=ft.Scale(0.94, alignment=ft.Alignment.TOP_CENTER),
        animate_opacity=ANIM_FAST,
        animate_scale=ANIM_FAST,
        shadow=MENU_SHADOW,
    )

    def set_chevron(opened: bool) -> None:
        icon = chevron_ref.current
        if icon is None:
            return
        icon.rotate = ft.Rotate(math.pi, alignment=ft.Alignment.CENTER) if opened else None

    def set_field_border(opened: bool) -> None:
        field = field_ref.current
        if field is None:
            return
        field.border = ft.Border.all(1, T.ACCENT if opened else T.BORDER)

    def remove_overlay() -> None:
        if menu_popup in page.overlay:
            page.overlay.remove(menu_popup)

    def _freeze_menu_animations() -> None:
        menu_popup.animate_opacity = None
        menu_popup.animate_scale = None
        menu_popup.opacity = 1

    def _resolve_field_width() -> float:
        field_width = state.get("field_width")
        if isinstance(field_width, (int, float)) and field_width > 0:
            return float(field_width)
        field = field_ref.current
        if field is not None and field.width:
            return float(field.width)
        return 280.0

    def close_menu(*, refresh: bool = True) -> None:
        global _select_scroll_reposition
        if not state["open"]:
            return
        state["open"] = False
        menu_popup.visible = False
        menu_popup.opacity = 0
        menu_popup.shadow = MENU_SHADOW
        menu_popup.top = None
        menu_popup.bottom = None
        menu_popup.width = None
        menu_popup.animate_opacity = ANIM_FAST
        menu_popup.animate_scale = ANIM_FAST
        scale_origin = (
            ft.Alignment.BOTTOM_CENTER
            if state.get("open_upward")
            else ft.Alignment.TOP_CENTER
        )
        menu_popup.scale = ft.Scale(0.94, alignment=scale_origin)
        set_chevron(False)
        set_field_border(False)
        remove_overlay()
        global _active_select_close
        if _active_select_close is close_menu:
            _active_select_close = None
        if _select_scroll_reposition is reposition_menu:
            _select_scroll_reposition = None
        _detach_page_keyboard(page)
        if refresh:
            page.update()

    def _sync_menu_item_widths() -> None:
        width = _resolve_field_width()
        inner = max(0.0, width - 2 * MENU_EDGE_INSET)
        menu_col.width = inner
        for ctrl in menu_col.controls:
            ctrl.width = inner

    def rebuild_menu() -> None:
        menu_col.controls.clear()
        for key, text in options:
            active = key == state["value"]
            trailing_controls: list[ft.Control] = []
            if option_trailing:
                extra = option_trailing(key)
                if extra is not None:
                    trailing_controls.append(extra)
            if active:
                trailing_controls.append(
                    ft.Icon(ft.Icons.CHECK, size=16, color=T.ACCENT)
                )
            item = ft.MenuItemButton(
                content=ft.Text(text, no_wrap=True),
                height=MENU_ITEM_HEIGHT,
                trailing=ft.Row(trailing_controls, spacing=4, tight=True)
                if trailing_controls
                else None,
                style=_select_menu_item_style(selected=active),
                on_click=lambda _e, k=key, t=text: choose(k, t),
            )
            menu_col.controls.append(item)

    def _apply_overlay_position(
        field_top: float,
        field_left: float,
        open_upward: bool,
    ) -> bool:
        menu_height = float(state.get("anchor_menu_height", 0))
        content_bottom = _content_bottom(page)
        if (
            not open_upward
            and field_top + T.FIELD_HEIGHT + MENU_GAP + menu_height > content_bottom - 4
            and field_top - MENU_GAP >= menu_height
        ):
            open_upward = True

        if open_upward:
            top = max(4.0, field_top - menu_height - MENU_GAP)
        else:
            top = field_top + T.FIELD_HEIGHT + MENU_GAP
            if top + menu_height > content_bottom - 4:
                top = max(4.0, content_bottom - menu_height - 4)

        menu_popup.bottom = None
        menu_popup.top = top
        menu_popup.left = field_left
        return open_upward

    def reposition_menu(scroll_pixels: float) -> None:
        if not state.get("open"):
            return
        delta = scroll_pixels - float(state.get("anchor_scroll", 0))
        field_top = float(state["anchor_field_top"]) - delta
        field_left = float(state["anchor_field_left"])
        open_upward = bool(state.get("open_upward"))
        state["open_upward"] = _apply_overlay_position(field_top, field_left, open_upward)
        _raise_menu_overlay(page, menu_popup)
        if menu_popup.page:
            menu_popup.update()

    def _menu_position(e: ft.TapEvent) -> tuple[float, float, bool, float] | None:
        global_coords = _global_from_tap(e)
        if global_coords is None:
            return None

        field_left, field_top = global_coords
        menu_height = _placement_menu_height(len(options), resolved_menu_height)
        content_bottom = _content_bottom(page)
        open_upward = _should_open_upward(field_top, menu_height, content_bottom)
        return field_left, field_top, open_upward, menu_height

    def open_menu(e: ft.TapEvent) -> None:
        global _select_scroll_reposition
        _close_active_select(refresh=False)
        rebuild_menu()
        placement = _menu_position(e)
        if placement is None:
            return
        field_left, field_top, open_upward, menu_height = placement
        state["anchor_field_top"] = field_top
        state["anchor_field_left"] = field_left
        state["anchor_scroll"] = getattr(page, "_tigo_page_scroll_offset", 0) or 0
        state["anchor_menu_height"] = menu_height
        open_upward = _apply_overlay_position(field_top, field_left, open_upward)
        scale_origin = (
            ft.Alignment.BOTTOM_CENTER if open_upward else ft.Alignment.TOP_CENTER
        )
        menu_popup.width = _resolve_field_width()
        _sync_menu_item_widths()
        menu_popup.visible = True
        menu_popup.opacity = 1
        menu_popup.shadow = MENU_SHADOW
        menu_popup.scale = ft.Scale(1, alignment=scale_origin)
        state["open"] = True
        state["open_upward"] = open_upward
        set_chevron(True)
        set_field_border(True)

        remove_overlay()
        _raise_menu_overlay(page, menu_popup)

        global _active_select_close
        _active_select_close = close_menu
        _select_scroll_reposition = reposition_menu

        _attach_page_keyboard(page)
        page.update()
        _freeze_menu_animations()

    def on_field_tap(e: ft.TapEvent) -> None:
        if disabled:
            return
        if state["open"]:
            close_menu()
        else:
            open_menu(e)

    def choose(key: str, text: str) -> None:
        state["value"] = key
        value_text.value = text
        value_text.color = T.TEXT
        close_menu(refresh=False)
        page.update()
        if on_change:
            on_change(key)

    def on_field_size(e: ft.LayoutSizeChangeEvent) -> None:
        if e.width > 0:
            state["field_width"] = e.width

    chevron = ft.Icon(
        ft.Icons.EXPAND_MORE,
        ref=chevron_ref,
        color=T.TEXT_MUTED,
        size=18,
        animate_rotation=CHEVRON_ANIM,
    )

    field = ft.Container(
        ref=field_ref,
        content=ft.Row(
            [value_text, chevron],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=T.FIELD_HEIGHT,
        bgcolor=T.ELEVATED,
        border=ft.Border.all(1, T.BORDER),
        border_radius=T.RADIUS_PILL,
        padding=ft.Padding.symmetric(horizontal=14, vertical=0),
        on_size_change=on_field_size,
        opacity=0.72 if disabled else 1.0,
    )

    rebuild_menu()

    return ft.Column(
        [
            ui_text(label, size=T.FONT_LABEL, color=T.TEXT_MUTED, weight=ft.FontWeight.W_500),
            ft.GestureDetector(
                content=field,
                on_tap=on_field_tap,
            ),
        ],
        spacing=T.SPACE_LABEL,
        tight=True,
    )


def _log_panel(content: ft.Control, *, height: int) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=T.ELEVATED,
        border=ft.Border.all(1, T.BORDER),
        border_radius=T.RADIUS,
        padding=12,
        height=height,
        expand=True,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def _refresh_control(control: ft.Control) -> None:
    """Update a control only when it is mounted on the page."""
    if not getattr(control, "page", None):
        return
    try:
        control.update()
    except RuntimeError as exc:
        if "must be added to the page first" not in str(exc):
            raise


def test_log_console(page: ft.Page) -> tuple[ft.Container, Callable[[], None]]:
    """Read-only colored log for strategy testing."""
    from src.modules.strategy_testing import journal as tls

    log_text = ft.Text(
        spans=[],
        size=T.FONT_CAPTION,
        color=T.TEXT,
        font_family=T.FONT_MONO,
        selectable=True,
    )

    log_column = ft.Column(
        [log_text],
        expand=True,
        scroll=ft.ScrollMode.ALWAYS,
    )

    def _build_spans() -> list[ft.TextSpan]:
        lines = tls.get_lines()
        if not lines:
            return [
                ft.TextSpan(
                    " ",
                    style=ft.TextStyle(
                        color=T.TEXT_MUTED,
                        font_family=T.FONT_MONO,
                        size=T.FONT_CAPTION,
                    ),
                )
            ]
        layout = tls.compute_table_layout(lines)
        spans: list[ft.TextSpan] = []
        mono = ft.TextStyle(font_family=T.FONT_MONO, size=T.FONT_CAPTION)
        for index, line in enumerate(lines):
            if index:
                spans.append(ft.TextSpan("\n", style=mono))
            for chunk, color in tls.line_text_spans(line, layout=layout):
                if not chunk:
                    continue
                spans.append(
                    ft.TextSpan(
                        chunk,
                        style=ft.TextStyle(color=color, font_family=T.FONT_MONO, size=T.FONT_CAPTION),
                    )
                )
        return spans

    def rebuild() -> None:
        log_text.value = ""
        log_text.spans = _build_spans()
        _refresh_control(log_text)

    tls.subscribe(rebuild)

    def unsubscribe() -> None:
        tls.unsubscribe(rebuild)

    return (
        _log_panel(
            ft.SelectionArea(content=log_column),
            height=LOG_PANEL_HEIGHT_TEST,
        ),
        unsubscribe,
    )

section = block_section
