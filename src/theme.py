"""Factiosi Paleta Umbrae — blue portal, dark & light."""

from __future__ import annotations

from typing import Literal, TypedDict

ThemeMode = Literal["dark", "light"]
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


class PortalPalette(TypedDict):
    id: str
    hue: PortalHue
    mode: ThemeMode
    label_ru: str
    ground: str
    surface: str
    elevated: str
    overlay: str
    accent: str
    accent_dim: str
    accent_soft: str
    overlay_hover: str
    text: str
    text_muted: str
    text_faint: str
    border: str
    border_strong: str


def _mix(base: tuple[int, int, int], accent: str, t: float) -> str:
    n = accent.removeprefix("#")
    ar, ag, ab = int(n[0:2], 16), int(n[2:4], 16), int(n[4:6], 16)
    r = int(base[0] * (1 - t) + ar * t)
    g = int(base[1] * (1 - t) + ag * t)
    b = int(base[2] * (1 - t) + ab * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _rgb(hex_color: str) -> tuple[int, int, int]:
    n = hex_color.removeprefix("#")
    return int(n[0:2], 16), int(n[2:4], 16), int(n[4:6], 16)


def _shade(base: tuple[int, int, int], target: str, t: float) -> str:
    tr, tg, tb = _rgb(target)
    r = int(base[0] * (1 - t) + tr * t)
    g = int(base[1] * (1 - t) + tg * t)
    b = int(base[2] * (1 - t) + tb * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def pack(
    hue: PortalHue,
    mode: ThemeMode,
    label_ru: str,
    *,
    ground: str,
    surface: str,
    elevated: str,
    overlay: str,
    accent: str,
    accent_dim: str,
    text: str | None = None,
    text_muted: str | None = None,
    text_faint: str | None = None,
) -> PortalPalette:
    dark = mode == "dark"
    if text is None:
        text = "#dce8f4" if hue == "blue" and dark else ("#e8e0f4" if dark else "#1a1424")
    if text_muted is None:
        text_muted = "#8699a8" if hue == "blue" and dark else ("#8c8699" if dark else "#6a6474")
    if text_faint is None:
        text_faint = "#566870" if hue == "blue" and dark else ("#5c5668" if dark else "#8a8494")

    soft_a = 0.12 if dark else 0.14
    hover_t = 0.10
    border_t = 0.22 if dark else 0.28
    border_s = 0.35 if dark else 0.42
    ground_rgb = _rgb(ground)
    overlay_rgb = _rgb(overlay)
    accent_soft = _mix(ground_rgb, accent, soft_a)
    overlay_hover = _shade(overlay_rgb, "#000000", hover_t)
    border = _mix(ground_rgb, accent, border_t)
    border_strong = _mix(ground_rgb, accent, border_s)

    return {
        "id": f"{hue}-{mode}",
        "hue": hue,
        "mode": mode,
        "label_ru": label_ru,
        "ground": ground,
        "surface": surface,
        "elevated": elevated,
        "overlay": overlay,
        "accent": accent,
        "accent_dim": accent_dim,
        "accent_soft": accent_soft,
        "overlay_hover": overlay_hover,
        "text": text,
        "text_muted": text_muted,
        "text_faint": text_faint,
        "border": border,
        "border_strong": border_strong,
    }


PALETTES: list[PortalPalette] = [
    pack("purple", "dark", "Фиолетовый · Dark", ground="#0c0b12", surface="#0f0d18", elevated="#16131f", overlay="#1c1828", accent="#c9a0e8", accent_dim="#9b6fc4"),
    pack("purple", "light", "Фиолетовый · Light", ground="#f3eff7", surface="#ebe4f2", elevated="#e0d6ec", overlay="#f8f5fb", accent="#7a4a9e", accent_dim="#5c3578", text="#1a1424", text_muted="#6a6474", text_faint="#8a8494"),
    pack("green", "dark", "Зелёный · Dark", ground="#0a100c", surface="#0d1410", elevated="#141c17", overlay="#1a241e", accent="#9db89a", accent_dim="#6a8f6e"),
    pack("green", "light", "Зелёный · Light", ground="#eef3ef", surface="#e4ebe5", elevated="#d8e2da", overlay="#f6f9f6", accent="#3d6b4f", accent_dim="#2a4d38", text="#101510", text_muted="#585e58", text_faint="#787e78"),
    pack("blue", "dark", "Синий · Dark", ground="#0a0e14", surface="#0d1219", elevated="#141b24", overlay="#1a222e", accent="#8aafd4", accent_dim="#4a7aa8"),
    pack("blue", "light", "Синий · Light", ground="#eef1f5", surface="#e3e8ef", elevated="#d5dde8", overlay="#f5f7fa", accent="#3a5f8a", accent_dim="#274366", text="#10151c", text_muted="#585e68", text_faint="#787e88"),
    pack("burgundy", "dark", "Бордовый · Dark", ground="#11090a", surface="#170d0f", elevated="#211316", overlay="#2a181b", accent="#ae5c55", accent_dim="#712f34"),
    pack("burgundy", "light", "Бордовый · Light", ground="#f5eeee", surface="#ebe1e1", elevated="#e0d2d2", overlay="#faf5f5", accent="#7c3030", accent_dim="#541f24", text="#1a1010", text_muted="#6a5858", text_faint="#8a7878"),
    pack("yellow", "dark", "Жёлтый · Dark", ground="#100d06", surface="#151108", elevated="#1d180d", overlay="#272012", accent="#d0aa45", accent_dim="#92702a"),
    pack("yellow", "light", "Жёлтый · Light", ground="#f5f1e5", surface="#ebe4d3", elevated="#e0d6bf", overlay="#faf8ef", accent="#85631b", accent_dim="#594211", text="#1a1408", text_muted="#6a6050", text_faint="#8a8070"),
    pack("brown", "dark", "Коричневый · Dark", ground="#0f0a08", surface="#16100d", elevated="#1e1611", overlay="#281d16", accent="#ad866c", accent_dim="#704a35"),
    pack("brown", "light", "Коричневый · Light", ground="#f2ece7", surface="#e7ddd5", elevated="#dacdc3", overlay="#f8f4f0", accent="#65402c", accent_dim="#432719", text="#1a1008", text_muted="#6a5850", text_faint="#8a7870"),
    pack("orange", "dark", "Оранжевый · Dark", ground="#120b05", surface="#181006", elevated="#221609", overlay="#2d1b0c", accent="#dc7b28", accent_dim="#ac4d0d"),
    pack("orange", "light", "Оранжевый · Light", ground="#f7efe5", surface="#ede2d2", elevated="#e3d3bd", overlay="#fcf6ed", accent="#a9470d", accent_dim="#71300a", text="#1a1005", text_muted="#6a5848", text_faint="#8a7868"),
    pack("mono", "dark", "Монохром · Dark", ground="#0a0a0a", surface="#111111", elevated="#1a1a1a", overlay="#222222", accent="#d0d0d0", accent_dim="#888888", text="#e8e8e8", text_muted="#999999", text_faint="#666666"),
    pack("mono", "light", "Монохром · Light", ground="#f5f5f5", surface="#ebebeb", elevated="#e0e0e0", overlay="#fafafa", accent="#2a2a2a", accent_dim="#555555", text="#1a1a1a", text_muted="#666666", text_faint="#888888"),
]

PORTAL_HUE_OPTIONS: list[tuple[PortalHue, str]] = [
    ("blue", "Синий"),
    ("purple", "Фиолетовый"),
    ("green", "Зелёный"),
    ("burgundy", "Бордовый"),
    ("yellow", "Жёлтый"),
    ("brown", "Коричневый"),
    ("orange", "Оранжевый"),
    ("mono", "Монохром"),
]

DEFAULT_PORTAL_HUE: PortalHue = "blue"
DEFAULT_THEME_MODE: ThemeMode = "dark"

STATUS_DARK = {
    "active": ("#7dce82", "#1a3a24"),
    "connecting": ("#90bcf0", "#1a2e3a"),
    "expiring": ("#e8be80", "#3a2e1a"),
    "error": ("#e87d7d", "#3a1a1a"),
    "offline": ("#6a6575", "#1a1a24"),
}

STATUS_LIGHT = {
    "active": ("#2e7d45", "#dcefe3"),
    "connecting": ("#2a5f8a", "#dce8f5"),
    "expiring": ("#8a5a18", "#f5ecd8"),
    "error": ("#a83232", "#f5dede"),
    "offline": ("#585e68", "#e3e6eb"),
}


def get_palette(
    *,
    hue: PortalHue = DEFAULT_PORTAL_HUE,
    mode: ThemeMode = DEFAULT_THEME_MODE,
) -> PortalPalette:
    palette_id = f"{hue}-{mode}"
    for p in PALETTES:
        if p["id"] == palette_id:
            return p
    return PALETTES[0]


class ThemeTokens:
    def __init__(self, palette: PortalPalette) -> None:
        self._p = palette
        self.mode = palette["mode"]
        self.hue = palette["hue"]

        self.GROUND = palette["ground"]
        self.SURFACE = palette["surface"]
        self.ELEVATED = palette["elevated"]
        self.OVERLAY = palette["overlay"]
        self.ACCENT = palette["accent"]
        self.ACCENT_DIM = palette["accent_dim"]
        self.ACCENT_SOFT = palette["accent_soft"]
        self.OVERLAY_HOVER = palette["overlay_hover"]
        self.MENU_SELECTED = palette["accent"]
        if palette["hue"] == "mono":
            self.MENU_SELECTED = palette["text"]
        self.TEXT = palette["text"]
        self.TEXT_MUTED = palette["text_muted"]
        self.TEXT_FAINT = palette["text_faint"]
        self.BORDER = palette["border"]
        self.BORDER_STRONG = palette["border_strong"]
        dark = self.mode == "dark"
        self.ON_ACCENT = palette["ground"] if dark else "#f5f7fa"

        # Legacy aliases used across UI helpers.
        self.PURPLE = self.ACCENT
        self.PURPLE_DIM = self.ACCENT_DIM
        self.PURPLE_SOFT = self.ACCENT_SOFT

        status = STATUS_DARK if dark else STATUS_LIGHT
        self.STATUS_ACTIVE = status["active"][0]
        self.STATUS_ACTIVE_BG = status["active"][1]
        self.STATUS_CONNECTING = status["connecting"][0]
        self.STATUS_CONNECTING_BG = status["connecting"][1]
        self.STATUS_EXPIRING = status["expiring"][0]
        self.STATUS_EXPIRING_BG = status["expiring"][1]
        self.STATUS_ERROR = status["error"][0]
        self.STATUS_ERROR_BG = status["error"][1]
        self.STATUS_OFFLINE = status["offline"][0]
        self.STATUS_OFFLINE_BG = status["offline"][1]

        self.FONT_FAMILY = "Segoe UI"
        self.FONT_MONO = "JetBrains Mono"
        self.FONT_BODY = 14
        self.FONT_LABEL = 13
        self.FONT_CAPTION = 12
        self.FONT_TITLE = 22

        self.SPACE_LABEL = 6
        self.SPACE_FIELD = 16
        self.SPACE_SECTION = 16
        self.SPACE_ROW = 12
        self.FIELD_HEIGHT = 40
        self.CONTROL_SLOT = 40
        self.RADIUS = 16
        self.RADIUS_PILL = 999
        self.SECTION_PAD = 20

        self.SIDEBAR_WIDTH = 268


def build_theme_tokens(
    mode: ThemeMode = DEFAULT_THEME_MODE,
    hue: PortalHue = DEFAULT_PORTAL_HUE,
) -> ThemeTokens:
    return ThemeTokens(get_palette(hue=hue, mode=mode))


_active_tokens = build_theme_tokens(DEFAULT_THEME_MODE, DEFAULT_PORTAL_HUE)


class ThemeProxy:
    """Stable import target; always reflects the active token set."""

    def __getattr__(self, name: str):
        return getattr(_active_tokens, name)

    def __repr__(self) -> str:
        return f"ThemeProxy(mode={_active_tokens.mode!r})"


# Import as `from src.theme import T` — do not rebind; use set_theme_mode().
T = ThemeProxy()


def apply_theme(mode: ThemeMode, hue: PortalHue = DEFAULT_PORTAL_HUE) -> ThemeTokens:
    global _active_tokens
    _active_tokens = build_theme_tokens(mode, hue)
    return _active_tokens


def set_theme_mode(mode: ThemeMode) -> ThemeTokens:
    return apply_theme(mode, _active_tokens.hue)


def build_flet_theme(tokens: ThemeTokens):
    """Build a Flet Theme for the given token set (light or dark)."""
    import flet as ft

    hover_overlay = tokens.ACCENT_SOFT
    menu_item_style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=6),
        color=tokens.TEXT,
        overlay_color={
            ft.ControlState.HOVERED: hover_overlay,
            ft.ControlState.FOCUSED: hover_overlay,
            ft.ControlState.PRESSED: hover_overlay,
        },
        bgcolor={
            ft.ControlState.SELECTED: tokens.ACCENT_SOFT,
        },
        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        visual_density=ft.VisualDensity.COMPACT,
    )
    outlined_style = ft.ButtonStyle(
        color=tokens.ACCENT,
        overlay_color={
            ft.ControlState.HOVERED: hover_overlay,
            ft.ControlState.FOCUSED: hover_overlay,
            ft.ControlState.PRESSED: hover_overlay,
        },
    )
    filled_style = ft.ButtonStyle(
        bgcolor=tokens.ACCENT,
        color=tokens.ON_ACCENT,
        overlay_color={
            ft.ControlState.HOVERED: tokens.ACCENT_DIM,
            ft.ControlState.FOCUSED: tokens.ACCENT_DIM,
            ft.ControlState.PRESSED: tokens.ACCENT_DIM,
        },
    )
    menu_style = ft.MenuStyle(
        bgcolor=tokens.OVERLAY,
        elevation=10,
        shadow_color="#00000080",
        shape=ft.RoundedRectangleBorder(radius=14),
        side=ft.BorderSide(1, tokens.BORDER),
        padding=8,
    )

    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=tokens.ACCENT,
            on_primary=tokens.ON_ACCENT,
            primary_container=tokens.ACCENT_SOFT,
            on_primary_container=tokens.ACCENT,
            secondary=tokens.ACCENT_DIM,
            on_secondary=tokens.ON_ACCENT,
            surface=tokens.SURFACE,
            on_surface=tokens.TEXT,
            on_surface_variant=tokens.TEXT_MUTED,
            outline=tokens.BORDER,
            outline_variant=tokens.BORDER_STRONG,
            error=tokens.STATUS_ERROR,
            on_error=tokens.ON_ACCENT,
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
                size=tokens.FONT_LABEL, font_family=tokens.FONT_FAMILY, color=tokens.TEXT_MUTED
            ),
            label_medium=ft.TextStyle(
                size=tokens.FONT_LABEL, font_family=tokens.FONT_FAMILY, color=tokens.TEXT_MUTED
            ),
            title_large=ft.TextStyle(
                size=tokens.FONT_TITLE, font_family=tokens.FONT_FAMILY, color=tokens.TEXT
            ),
        ),
        splash_color=hover_overlay,
        hover_color=hover_overlay,
        highlight_color=hover_overlay,
        focus_color=tokens.ACCENT_SOFT,
        scaffold_bgcolor=tokens.GROUND,
        canvas_color=tokens.GROUND,
        popup_menu_theme=ft.PopupMenuTheme(
            color=tokens.OVERLAY,
            shadow_color="#00000080",
            icon_color=tokens.ACCENT,
            label_text_style=ft.TextStyle(color=tokens.TEXT, size=tokens.FONT_BODY),
            elevation=10,
            shape=ft.RoundedRectangleBorder(radius=14),
            menu_padding=8,
        ),
        dropdown_theme=ft.DropdownTheme(
            menu_style=menu_style,
            text_style=ft.TextStyle(color=tokens.TEXT, size=tokens.FONT_BODY),
        ),
        text_button_theme=ft.TextButtonTheme(style=menu_item_style),
        outlined_button_theme=ft.OutlinedButtonTheme(style=outlined_style),
        filled_button_theme=ft.FilledButtonTheme(style=filled_style),
    )
