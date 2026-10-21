"""Знаки Tigo в материале Factiosi Umbrae: хром, неон, звёздный блик.

Вход: белый силуэт assets/brand/sources/tigo-simple.svg и токены src/ui/theme/umbrae.py.
Выход: SVG в assets/icons/ (окно, трей, знак окна обновления). Растры из них делает generate_icons.mjs.
Запуск из корня: python tools/build_brand.py, затем python tools/generate_icons.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ui.theme.umbrae import DARK  # noqa: E402

SOURCE = ROOT / "assets" / "brand" / "sources" / "tigo-simple.svg"
ICONS = ROOT / "assets" / "icons"

# Рамка силуэта в координатах 1024: по ней идёт вертикальный градиент хрома.
MARK_TOP, MARK_BOTTOM = 50, 974
# Острый левый верхний угол щита — место звёздного блика (docs/UMBRAE.md, «Звёздный блик»).
FLARE_AT = (96, 155)
CHROME_STOPS = (0, 0.3, 0.47, 0.52, 0.6, 0.82, 1)
FLARE_PATH = "M0,-150 L18,-18 L255,0 L18,18 L0,150 L-18,18 L-255,0 L-18,-18 Z"


def _rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def _hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def grey(value: str) -> str:
    """Тот же металл без оттенка: яркость по Rec. 709."""
    r, g, b = _rgb(value)
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return _hex((y, y, y))


def tint(value: str, toward: str, amount: float) -> str:
    """Серый металл с отливом: смесь яркости и цвета по мере светлоты, тени остаются тенями."""
    y = _rgb(grey(value))[0]
    t = _rgb(toward)
    return _hex(y + (c * y / 255 - y) * amount for c in t)


def chrome_scheme(scheme: dict[str, str], recolor) -> dict[str, str]:
    out = dict(scheme)
    for i in range(len(CHROME_STOPS)):
        key = f"umbrae-chrome-{i}"
        out[key] = recolor(scheme[key])
    return out


def glyphs() -> str:
    svg = SOURCE.read_text(encoding="utf-8")
    return "\n".join(re.findall(r"\s*<path[^>]*/>", svg))


def chrome_gradient(scheme: dict[str, str]) -> str:
    stops = "\n".join(
        f'      <stop offset="{offset}" stop-color="{scheme[f"umbrae-chrome-{i}"]}"/>'
        for i, offset in enumerate(CHROME_STOPS)
    )
    return (
        f'    <linearGradient id="chrome" gradientUnits="userSpaceOnUse" x1="0" y1="{MARK_TOP}" x2="0" y2="{MARK_BOTTOM}">\n'
        f"{stops}\n    </linearGradient>"
    )


def mark_svg(
    scheme: dict[str, str],
    *,
    glow: str,
    glow_opacity: float,
    core: str,
    glow_width: int,
    core_width: int,
    glow_blur: int,
    flare: bool,
    comment: str,
) -> str:
    flare_defs = flare_layer = ""
    if flare:
        sheen = scheme["umbrae-sheen"]
        flare_defs = f"""
    <path id="flare" d="{FLARE_PATH}"/>
    <filter id="flare-glow" x="-100%" y="-200%" width="300%" height="500%" color-interpolation-filters="sRGB">
      <feGaussianBlur stdDeviation="30"/>
    </filter>
    <filter id="flare-soft" x="-50%" y="-100%" width="200%" height="300%" color-interpolation-filters="sRGB">
      <feGaussianBlur stdDeviation="5"/>
    </filter>"""
        x, y = FLARE_AT
        flare_layer = f"""
  <g transform="translate({x} {y}) rotate(45) scale(0.45)">
    <use href="#flare" fill="{glow}" opacity="0.6" filter="url(#flare-glow)"/>
    <use href="#flare" fill="{sheen}" opacity="0.8" filter="url(#flare-soft)"/>
  </g>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- {comment} Собрано tools/build_brand.py — руками не править. -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
{chrome_gradient(scheme)}
    <filter id="neon" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB">
      <feGaussianBlur stdDeviation="{glow_blur}"/>
    </filter>
    <g id="mark">
{glyphs()}
    </g>{flare_defs}
  </defs>
  <use href="#mark" fill="none" stroke="{glow}" stroke-width="{glow_width}" stroke-linejoin="round" opacity="{glow_opacity}" filter="url(#neon)"/>
  <use href="#mark" fill="url(#chrome)"/>
  <use href="#mark" fill="none" stroke="{core}" stroke-width="{core_width}" stroke-linejoin="round"/>{flare_layer}
</svg>
"""


def main() -> None:
    dark_glow = float(DARK["umbrae-neon-glow-opacity"])
    outputs = {
        # Окно и ярлыки: полный материал со звёздным бликом.
        "app.svg": mark_svg(
            DARK, glow=DARK["umbrae-neon-glow"], glow_opacity=dark_glow, core=DARK["umbrae-neon-core"],
            glow_width=40, core_width=12, glow_blur=18, flare=True, comment="Tigo: значок окна.",
        ),
        # Окно обновления TigoUpdate: тот же знак на почти чёрном фоне.
        "mark-dark.svg": mark_svg(
            DARK, glow=DARK["umbrae-neon-glow"], glow_opacity=dark_glow, core=DARK["umbrae-neon-core"],
            glow_width=40, core_width=12, glow_blur=18, flare=True, comment="Tigo: знак окна обновления.",
        ),
        # Трей мелкий: ореол шире, сердцевина толще, без звезды.
        # Покой — чёрно-белый металл и белёсый неон; работа — металл с зелёным отливом и неон цвета успеха.
        "tray-idle.svg": mark_svg(
            chrome_scheme(DARK, grey), glow=grey(DARK["umbrae-neon-glow"]), glow_opacity=0.9,
            core=grey(DARK["umbrae-neon-core"]), glow_width=70, core_width=26, glow_blur=26,
            flare=False, comment="Tigo: трей, покой.",
        ),
        "tray-active.svg": mark_svg(
            chrome_scheme(DARK, lambda c: tint(c, DARK["feedback-success-text"], 0.35)),
            glow=DARK["feedback-success-text"], glow_opacity=0.95,
            core=DARK["feedback-success-text"], glow_width=70, core_width=26, glow_blur=26,
            flare=False, comment="Tigo: трей, работа.",
        ),
    }
    for name, svg in outputs.items():
        (ICONS / name).write_text(svg, encoding="utf-8", newline="\n")
        print("OK", name)


if __name__ == "__main__":
    main()
