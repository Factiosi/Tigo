"""Win32 tray icon with bitmap menu items."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

import pystray
from PIL import Image

if sys.platform != "win32":
    raise RuntimeError("Win32 tray icons are only supported on Windows.")

from pystray._util import win32


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _BITMAPINFOHEADER)]


_gdi32 = ctypes.windll.gdi32


def pil_to_hbitmap(image: Image.Image) -> wintypes.HBITMAP:
    """Convert a PIL image to an HBITMAP for menu item icons."""
    rgba = image.convert("RGBA")
    width, height = rgba.size
    bmi = _BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0
    bits = ctypes.c_void_p()
    hbmp = _gdi32.CreateDIBSection(
        None,
        ctypes.byref(bmi),
        0,
        ctypes.byref(bits),
        None,
        0,
    )
    if not hbmp:
        raise OSError("CreateDIBSection failed")
    buffer = rgba.tobytes("raw", "BGRA")
    ctypes.memmove(bits, buffer, len(buffer))
    return hbmp


def menu_item(text: str, action, *, icon: Image.Image | None = None, **kwargs) -> pystray.MenuItem:
    """Create a tray menu item with an optional Win32 bitmap icon."""
    item = pystray.MenuItem(text, action, **kwargs)
    if icon is not None:
        setattr(item, "menu_icon", icon)
    return item


class TigoTrayIcon(pystray._win32.Icon):
    """pystray Win32 icon that renders optional menu item bitmaps."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._menu_bitmaps: list[wintypes.HBITMAP] = []

    def _release_menu_bitmaps(self) -> None:
        for hbmp in self._menu_bitmaps:
            try:
                _gdi32.DeleteObject(hbmp)
            except Exception:  # noqa: BLE001
                pass
        self._menu_bitmaps.clear()

    def _update_menu(self) -> None:
        self._release_menu_bitmaps()
        super()._update_menu()

    def _create_menu_item(self, descriptor, callbacks):
        item = super()._create_menu_item(descriptor, callbacks)
        icon = getattr(descriptor, "menu_icon", None)
        if icon is not None and descriptor is not pystray.Menu.SEPARATOR:
            hbmp = pil_to_hbitmap(icon)
            self._menu_bitmaps.append(hbmp)
            item.fMask |= win32.MIIM_BITMAP
            item.hbmpItem = hbmp
        return item

    def stop(self) -> None:
        self._release_menu_bitmaps()
        super().stop()
