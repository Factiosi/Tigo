"""Tigo logo paths and raster tray/window assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.core.paths import program_root


def logos_dir() -> Path:
    return program_root() / "logos"


def online_dir() -> Path:
    return logos_dir() / "online"


def offline_dir() -> Path:
    return logos_dir() / "offline"


def app_window_icon_path() -> Path | None:
    """Always-online icon for the app window and shortcuts."""
    ico = online_dir() / "tigo.ico"
    return ico if ico.exists() else None


def tray_icon_path(*, running: bool) -> Path:
    folder = online_dir() if running else offline_dir()
    png = folder / "tigo-tray.png"
    if png.exists():
        return png
    fallback = online_dir() / "tigo-tray.png"
    return fallback if fallback.exists() else png


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
    "load_tray_icon",
    "logos_dir",
    "offline_dir",
    "online_dir",
    "tray_icon_path",
]
