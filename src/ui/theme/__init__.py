"""Схема Tigo: поверхности Leo и акцент категории rete. Второй палитры нет."""

from __future__ import annotations

from typing import Literal, TypedDict

ThemeMode = Literal["dark", "light"]
# Поле settings.json со старых сборок. На экран не влияет: категория приложения — rete.
PortalHue = Literal[
    "purple",
    "green",
    "blue",
    "burgundy",
    "yellow",
    "brown",
    "orange",
    "mono",
]

# Итог scripts/build_theme.mjs, коммит Leo 7cacfef7134a605e35de9bb95db4e85540b941bc.
_SCHEME = {
    "light": {
        "page": "#fafafb",
        "card": "#ffffff",
        "raised": "#ffffff",
        "sunken": "#e4e4e5",
        "text": "#1c1c1d",
        "text_secondary": "#464649",
        "text_tertiary": "#727277",
        "line": "#e4e4e5",
        "line_strong": "#bcbcbd",
        "button": "#434fcf",
        "on_button": "#ffffff",
        "success": "#1d703b",
        "warning": "#745c00",
        "error": "#b10b15",
        "highlight": "#f2f2f3",
        "selected": "#eef2ff",
    },
    "dark": {
        "page": "#121213",
        "card": "#19191b",
        "raised": "#141415",
        "sunken": "#0f0f0f",
        "text": "#e4e4e5",
        "text_secondary": "#c7c7c9",
        "text_tertiary": "#929296",
        "line": "#303032",
        "line_strong": "#5e5e62",
        "button": "#bcc6f3",
        "on_button": "#212848",
        "success": "#45ca75",
        "warning": "#d4ab1e",
        "error": "#fc8276",
        "highlight": "#252527",
        "selected": "#1a1f38",
    },
}

_RETE = {
    "light": {"accent": "#224470", "hover": "#20416c", "active": "#1f3e68"},
    "dark": {"accent": "#7badfa", "hover": "#a9c8f9", "active": "#78a8f5"},
}

# Кольцо фокуса Leo: --leo-effect-focus-state, primitive-primary-50.
_FOCUS = "#5b67e8"


def argb(hex_color: str, alpha: int) -> str:
    """Flet берёт #AARRGGBB. Альфа в конце превращает цвет кнопки в оливковый."""
    return f"#{alpha:02x}{hex_color.removeprefix('#')}"


def ink(hex_color: str) -> str:
    """Чёрный или белый текст по яркости фона плашки."""
    raw = hex_color.removeprefix("#")
    red, green, blue = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#000000" if luminance > 150 else "#ffffff"


class PortalPalette(TypedDict):
    id: str
    mode: ThemeMode
    ground: str
    surface: str
    elevated: str
    overlay: str
    sunken: str
    accent: str
    accent_dim: str
    accent_soft: str
    overlay_hover: str
    selected: str
    text: str
    text_muted: str
    text_faint: str
    border: str
    border_strong: str
    button: str
    on_button: str
    focus: str
    success: str
    warning: str
    error: str


def get_palette(*, mode: ThemeMode = "dark", hue: str | None = None) -> PortalPalette:
    del hue  # категория Tigo зафиксирована: rete
    scheme = _SCHEME[mode]
    rete = _RETE[mode]
    return {
        "id": f"rete-{mode}",
        "mode": mode,
        "ground": scheme["page"],
        "surface": scheme["card"],
        "elevated": scheme["raised"],
        "overlay": scheme["card"],
        "sunken": scheme["sunken"],
        "accent": rete["accent"],
        "accent_dim": rete["active"],
        "accent_soft": argb(rete["accent"], 0x1F),
        "overlay_hover": scheme["highlight"],
        "selected": scheme["selected"],
        "text": scheme["text"],
        "text_muted": scheme["text_secondary"],
        "text_faint": scheme["text_tertiary"],
        "border": scheme["line"],
        "border_strong": scheme["line_strong"],
        "button": scheme["button"],
        "on_button": scheme["on_button"],
        "focus": _FOCUS,
        "success": scheme["success"],
        "warning": scheme["warning"],
        "error": scheme["error"],
    }


DEFAULT_THEME_MODE: ThemeMode = "dark"


class ThemeTokens:
    def __init__(self, palette: PortalPalette) -> None:
        self._p = palette
        self.mode = palette["mode"]
        self.hue = "rete"

        self.GROUND = palette["ground"]
        self.SURFACE = palette["surface"]
        self.ELEVATED = palette["elevated"]
        self.OVERLAY = palette["overlay"]
        self.SUNKEN = palette["sunken"]
        self.ACCENT = palette["accent"]
        self.ACCENT_DIM = palette["accent_dim"]
        self.ACCENT_SOFT = palette["accent_soft"]
        self.OVERLAY_HOVER = palette["overlay_hover"]
        self.SELECTED = palette["selected"]
        self.MENU_SELECTED = palette["button"]
        self.TEXT = palette["text"]
        self.TEXT_MUTED = palette["text_muted"]
        self.TEXT_FAINT = palette["text_faint"]
        self.BORDER = palette["border"]
        self.BORDER_STRONG = palette["border_strong"]
        self.BUTTON = palette["button"]
        self.ON_BUTTON = palette["on_button"]
        self.ON_ACCENT = palette["ground"] if self.mode == "dark" else "#ffffff"
        self.FOCUS = palette["focus"]

        self.PURPLE = self.ACCENT
        self.PURPLE_DIM = self.ACCENT_DIM
        self.PURPLE_SOFT = self.ACCENT_SOFT

        self.STATUS_ACTIVE = palette["success"]
        self.STATUS_ACTIVE_BG = palette["success"]
        self.STATUS_CONNECTING = palette["button"]
        self.STATUS_CONNECTING_BG = palette["button"]
        self.STATUS_EXPIRING = palette["warning"]
        self.STATUS_EXPIRING_BG = palette["warning"]
        self.STATUS_ERROR = palette["error"]
        self.STATUS_ERROR_BG = palette["error"]
        self.STATUS_OFFLINE = palette["border_strong"]
        self.STATUS_OFFLINE_BG = palette["border_strong"]
        # Выключенная дорожка переключателя Leo: outline-variant.
        self.TRACK_OFF = "#464649" if self.mode == "dark" else "#c9c9ca"
        self.HOVER_SCRIM = "#29000000" if self.mode == "dark" else "#29ffffff"
        self.PRESS_SCRIM = "#47000000" if self.mode == "dark" else "#47ffffff"
        self.OUTLINE_HOVER = argb(palette["button"], 0x1A)

        self.FONT_FAMILY = "Segoe UI"
        self.FONT_DISPLAY = "Cormorant"
        self.FONT_UI = "Inter"
        self.FONT_MONO = "JetBrains Mono"
        self.FONT_BODY = 14
        self.FONT_LABEL = 14
        self.FONT_CAPTION = 12
        self.FONT_TITLE = 28

        self.SPACE_LABEL = 4
        self.SPACE_FIELD = 16
        self.SPACE_SECTION = 16
        self.SPACE_ROW = 12
        self.FIELD_HEIGHT = 46
        self.BUTTON_HEIGHT = 44
        self.CONTROL_SLOT = 46
        self.RADIUS = 8
        self.RADIUS_L = 12
        self.RADIUS_PILL = 1000
        self.SECTION_PAD = 12

        self.SIDEBAR_WIDTH = 279


def build_theme_tokens(mode: ThemeMode = DEFAULT_THEME_MODE, hue: str | None = None) -> ThemeTokens:
    return ThemeTokens(get_palette(mode=mode, hue=hue))


_active_tokens = build_theme_tokens(DEFAULT_THEME_MODE)


class ThemeProxy:
    """Stable import target; always reflects the active token set."""

    def __getattr__(self, name: str):
        return getattr(_active_tokens, name)

    def __repr__(self) -> str:
        return f"ThemeProxy(mode={_active_tokens.mode!r})"


T = ThemeProxy()


def apply_theme(mode: ThemeMode, hue: str | None = None) -> ThemeTokens:
    global _active_tokens
    _active_tokens = build_theme_tokens(mode, hue)
    return _active_tokens


def set_theme_mode(mode: ThemeMode) -> ThemeTokens:
    return apply_theme(mode)


def build_flet_theme(tokens: ThemeTokens):
    """Build a Flet Theme for the given token set (light or dark)."""
    import flet as ft

    menu_item_style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS),
        color=tokens.TEXT,
        overlay_color={
            ft.ControlState.HOVERED: tokens.OVERLAY_HOVER,
            ft.ControlState.FOCUSED: tokens.OVERLAY_HOVER,
            ft.ControlState.PRESSED: tokens.OVERLAY_HOVER,
        },
        bgcolor={
            ft.ControlState.SELECTED: tokens.SELECTED,
        },
        padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        visual_density=ft.VisualDensity.COMPACT,
    )
    outlined_style = ft.ButtonStyle(
        color=tokens.BUTTON,
        overlay_color={
            ft.ControlState.HOVERED: tokens.OUTLINE_HOVER,
            ft.ControlState.FOCUSED: tokens.OUTLINE_HOVER,
            ft.ControlState.PRESSED: tokens.OUTLINE_HOVER,
        },
        shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_PILL),
        padding=ft.Padding.symmetric(horizontal=12, vertical=12),
        text_style=ft.TextStyle(
            size=tokens.FONT_BODY,
            font_family=tokens.FONT_UI,
            weight=ft.FontWeight.W_600,
        ),
    )
    filled_style = ft.ButtonStyle(
        bgcolor=tokens.BUTTON,
        color=tokens.ON_BUTTON,
        overlay_color={
            ft.ControlState.HOVERED: tokens.HOVER_SCRIM,
            ft.ControlState.FOCUSED: tokens.HOVER_SCRIM,
            ft.ControlState.PRESSED: tokens.PRESS_SCRIM,
        },
        shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_PILL),
        padding=ft.Padding.symmetric(horizontal=12, vertical=12),
        text_style=ft.TextStyle(
            size=tokens.FONT_BODY,
            font_family=tokens.FONT_UI,
            weight=ft.FontWeight.W_600,
        ),
    )
    menu_style = ft.MenuStyle(
        bgcolor=tokens.OVERLAY,
        elevation=8,
        shadow_color="#54000000" if tokens.mode == "dark" else "#14000000",
        shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_L),
        side=ft.BorderSide(1, tokens.BORDER),
        padding=4,
    )

    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=tokens.BUTTON,
            on_primary=tokens.ON_BUTTON,
            primary_container=tokens.SELECTED,
            on_primary_container=tokens.BUTTON,
            secondary=tokens.ACCENT,
            on_secondary=tokens.ON_ACCENT,
            surface=tokens.SURFACE,
            on_surface=tokens.TEXT,
            on_surface_variant=tokens.TEXT_MUTED,
            outline=tokens.BORDER,
            outline_variant=tokens.BORDER_STRONG,
            error=tokens.STATUS_ERROR,
            on_error=tokens.ON_BUTTON,
            surface_container_highest=tokens.OVERLAY,
        ),
        font_family=tokens.FONT_FAMILY,
        text_theme=ft.TextTheme(
            body_large=ft.TextStyle(
                size=tokens.FONT_BODY, font_family=tokens.FONT_FAMILY, color=tokens.TEXT
            ),
            body_medium=ft.TextStyle(
                size=tokens.FONT_BODY, font_family=tokens.FONT_FAMILY, color=tokens.TEXT
            ),
            body_small=ft.TextStyle(
                size=tokens.FONT_CAPTION, font_family=tokens.FONT_FAMILY, color=tokens.TEXT_MUTED
            ),
            label_large=ft.TextStyle(
                size=tokens.FONT_BODY, font_family=tokens.FONT_UI, color=tokens.TEXT, weight=ft.FontWeight.W_600
            ),
            label_medium=ft.TextStyle(
                size=tokens.FONT_CAPTION, font_family=tokens.FONT_FAMILY, color=tokens.TEXT_MUTED
            ),
            title_large=ft.TextStyle(
                size=tokens.FONT_TITLE, font_family=tokens.FONT_DISPLAY, color=tokens.TEXT, weight=ft.FontWeight.W_600
            ),
        ),
        splash_color="#00000000",
        hover_color=tokens.OVERLAY_HOVER,
        highlight_color=tokens.OVERLAY_HOVER,
        focus_color=tokens.FOCUS,
        scaffold_bgcolor=tokens.GROUND,
        canvas_color=tokens.GROUND,
        checkbox_theme=ft.CheckboxTheme(
            fill_color={
                ft.ControlState.SELECTED: tokens.BUTTON,
                ft.ControlState.DEFAULT: tokens.SURFACE,
            },
            check_color=tokens.ON_BUTTON,
            overlay_color={
                ft.ControlState.HOVERED: "#00000000",
                ft.ControlState.FOCUSED: "#00000000",
                ft.ControlState.PRESSED: "#00000000",
            },
        ),
        radio_theme=ft.RadioTheme(
            fill_color={
                ft.ControlState.SELECTED: tokens.BUTTON,
                ft.ControlState.DEFAULT: tokens.BORDER_STRONG,
            },
            overlay_color={
                ft.ControlState.HOVERED: "#00000000",
                ft.ControlState.FOCUSED: "#00000000",
                ft.ControlState.PRESSED: "#00000000",
            },
        ),
        popup_menu_theme=ft.PopupMenuTheme(
            color=tokens.OVERLAY,
            shadow_color="#54000000" if tokens.mode == "dark" else "#14000000",
            icon_color=tokens.TEXT_MUTED,
            label_text_style=ft.TextStyle(color=tokens.TEXT, size=tokens.FONT_BODY, font_family=tokens.FONT_FAMILY),
            elevation=8,
            shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_L),
            menu_padding=4,
        ),
        dropdown_theme=ft.DropdownTheme(
            menu_style=menu_style,
            text_style=ft.TextStyle(color=tokens.TEXT, size=tokens.FONT_BODY, font_family=tokens.FONT_FAMILY),
        ),
        text_button_theme=ft.TextButtonTheme(style=menu_item_style),
        outlined_button_theme=ft.OutlinedButtonTheme(style=outlined_style),
        filled_button_theme=ft.FilledButtonTheme(style=filled_style),
    )
