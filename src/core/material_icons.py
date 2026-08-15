"""Render Material Icons (same catalog as Flet UI) to PIL images."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.core.paths import program_root

_FONT_NAME = "MaterialIcons-Regular.otf"
_CATALOG_PATH = ("controls", "material", "icons.json")


@lru_cache(maxsize=1)
def _icons_catalog() -> dict[str, int]:
    import flet

    flet_root = Path(flet.__file__).resolve().parent
    catalog_path = flet_root.joinpath(*_CATALOG_PATH)
    with catalog_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return {str(name): int(codepoint) for name, codepoint in payload.items()}


def material_font_path() -> Path:
    candidates: list[Path] = [
        program_root()
        / "flet_client"
        / "data"
        / "flutter_assets"
        / "fonts"
        / _FONT_NAME,
        program_root() / "flet" / "data" / "flutter_assets" / "fonts" / _FONT_NAME,
    ]
    flet_cache = Path.home() / ".flet" / "client"
    if flet_cache.is_dir():
        matches = sorted(
            flet_cache.glob(f"flet-desktop-*/flet/data/flutter_assets/fonts/{_FONT_NAME}"),
            reverse=True,
        )
        candidates.extend(matches)
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "MaterialIcons-Regular.otf not found. Run Tigo once or build with bundled flet_client."
    )


def _hex_to_rgba(color: str, *, alpha: int = 255) -> tuple[int, int, int, int]:
    value = color.removeprefix("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB color, got {color!r}")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


def render_material_icon(icon_name: str, *, size: int = 16, color: str) -> Image.Image:
    """Rasterize a Material icon glyph to a square RGBA image."""
    catalog = _icons_catalog()
    try:
        codepoint = catalog[icon_name]
    except KeyError as exc:
        raise KeyError(f"Unknown Material icon: {icon_name}") from exc

    font = ImageFont.truetype(str(material_font_path()), size=max(size + 2, 18))
    glyph = chr(codepoint)
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), glyph, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2 - bbox[0]
    y = (size - text_h) // 2 - bbox[1]
    draw.text((x, y), glyph, font=font, fill=_hex_to_rgba(color))
    return image


__all__ = ["material_font_path", "render_material_icon"]
