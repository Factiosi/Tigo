"""Custom font resolution for Tigo."""

from __future__ import annotations

import os
from pathlib import Path

from src.core.paths import program_root

FONT_JETBRAINS_MONO = "JetBrains Mono"
FONT_CORMORANT = "Cormorant"
FONT_INTER = "Inter"


def jetbrains_mono_asset() -> Path:
    return program_root() / "assets" / "fonts" / "JetBrainsMono-Regular.ttf"


def resolve_jetbrains_mono_path() -> Path | None:
    bundled = jetbrains_mono_asset()
    if bundled.exists():
        return bundled.resolve()

    local_fonts = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"
    for name in (
        "JetBrainsMonoNL-Regular.ttf",
        "JetBrainsMono-Regular.ttf",
        "JetBrainsMono[wght].ttf",
    ):
        candidate = local_fonts / name
        if candidate.exists():
            return candidate.resolve()

    windows_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in ("JetBrainsMonoNL-Regular.ttf", "JetBrainsMono-Regular.ttf"):
        candidate = windows_fonts / name
        if candidate.exists():
            return candidate.resolve()
    return None


def register_mono_font(page) -> None:
    """Register JetBrains Mono and the house faces for Flet Text controls."""
    fonts = dict(page.fonts or {})
    path = resolve_jetbrains_mono_path()
    if path:
        fonts[FONT_JETBRAINS_MONO] = str(path)
    root = program_root() / "assets" / "fonts"
    cormorant = root / "Cormorant.ttf"
    inter = root / "Inter.ttf"
    if cormorant.exists():
        fonts[FONT_CORMORANT] = str(cormorant.resolve())
    if inter.exists():
        fonts[FONT_INTER] = str(inter.resolve())
    page.fonts = fonts
