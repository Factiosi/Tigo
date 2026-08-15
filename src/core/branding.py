"""Tigo icon paths and raster tray/window assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.core.material_icons import render_material_icon
from src.core.paths import program_root
from src.core.settings import get_settings
from src.theme import build_theme_tokens

_TRAY_MENU_SPECS: dict[str, tuple[str, str]] = {
    "start": ("PLAY_ARROW_OUTLINED", "STATUS_ACTIVE"),
    "stop": ("STOP", "STATUS_ERROR"),
    "open": ("OPEN_IN_NEW_OUTLINED", "ACCENT"),
    "quit": ("LOGOUT", "TEXT_MUTED"),
}


def icons_dir() -> Path:
    return program_root() / "icons"


def app_window_icon_path() -> Path | None:
    """Always-online icon for the app window and shortcuts."""
    ico = icons_dir() / "app.ico"
    return ico if ico.exists() else None


def tray_icon_path(*, running: bool) -> Path:
    name = "tray-active.png" if running else "tray-idle.png"
    path = icons_dir() / name
    if path.exists():
        return path
    fallback = icons_dir() / "tray-active.png"
    return fallback if fallback.exists() else path


def load_tray_menu_icon(name: str, *, size: int = 16) -> Image.Image | None:
    spec = _TRAY_MENU_SPECS.get(name)
    if spec is None:
        return None
    icon_name, token_name = spec
    settings = get_settings()
    tokens = build_theme_tokens(settings.theme_mode, settings.portal_hue)
    color = getattr(tokens, token_name, tokens.ACCENT)
    try:
        return render_material_icon(icon_name, size=size, color=color)
    except (FileNotFoundError, KeyError, OSError, ValueError):
        return None


def load_tray_icon(*, running: bool, size: int = 64) -> Image.Image:
    path = tray_icon_path(running=running)
    if not path.exists():
        return _fallback_tray_icon(size)
    image = Image.open(path).convert("RGBA")
    if image.size != (size, size):
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image


def _fallback_tray_icon(size: int) -> Image.Image:
    from PIL import ImageDraw

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, size - 4, size - 4), fill=(66, 133, 244, 255))
    return image


__all__ = [
    "app_window_icon_path",
    "icons_dir",
    "load_tray_icon",
    "load_tray_menu_icon",
    "tray_icon_path",
]
