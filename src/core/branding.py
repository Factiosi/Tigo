"""Tigo icon paths and raster tray/window assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.core.paths import program_root


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


def tray_menu_icon_path(name: str) -> Path:
    return icons_dir() / "menu" / f"{name}.png"


def load_tray_menu_icon(name: str, *, size: int = 16) -> Image.Image | None:
    path = tray_menu_icon_path(name)
    if not path.exists():
        return None
    image = Image.open(path).convert("RGB")
    if image.size != (size, size):
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image


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
    "tray_menu_icon_path",
]
