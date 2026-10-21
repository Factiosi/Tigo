"""Окно TigoUpdate в Factiosi Umbrae: знак в хроме, одна шкала с меняющейся подписью и короткий лог.

Чистый Win32 и GDI+ без Flet. Рамка обычная, от Windows, с тёмным заголовком: окно, которое
появляется само, не должно пугать. Шрифты как в Tigo: заголовки Inter полужирным, текст Segoe UI.
Цвета — только токены umbrae.py, своих hex здесь нет.
"""

from __future__ import annotations

import ctypes
import math
import sys
import time
from ctypes import wintypes
from pathlib import Path

from src.ui.theme.umbrae import DARK, px
from src.update_splash.worker import State, Worker

if sys.platform != "win32":
    raise RuntimeError("TigoUpdate работает только в Windows.")

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_gdi32 = ctypes.WinDLL("gdi32")
_kernel32 = ctypes.WinDLL("kernel32")
_dwmapi = ctypes.WinDLL("dwmapi")
_gdip = ctypes.WinDLL("gdiplus")

# Окно в логических пикселях: шкала DPI применяется при рисовании.
_W, _H = 440, 252
_PAD = px("space-card-padding")
_FRAME_MS = 33
_CLOSE_AFTER_DONE_S = 1.6
_BAR_SHEEN_PERIOD_S = 2.4

_WS_CAPTION = 0x00C00000
_WS_SYSMENU = 0x00080000
_WS_MINIMIZEBOX = 0x00020000
_WM_DESTROY = 0x0002
_WM_PAINT = 0x000F
_WM_CLOSE = 0x0010
_WM_ERASEBKGND = 0x0014
_WM_SETICON = 0x0080
_WM_TIMER = 0x0113
_WM_MOUSEMOVE = 0x0200
_WM_LBUTTONUP = 0x0202
_SRCCOPY = 0x00CC0020


def _argb(token: str, alpha: float = 1.0) -> int:
    value = DARK[token]
    if value.startswith("#"):
        r, g, b = (int(value[i : i + 2], 16) for i in (1, 3, 5))
        a = alpha
    else:
        parts = value[value.index("(") + 1 : value.index(")")].replace("/", " ").replace(",", " ").split()
        r, g, b = (int(p) for p in parts[:3])
        a = float(parts[3]) * alpha if len(parts) > 3 else alpha
    return (round(a * 255) << 24) | (r << 16) | (g << 8) | b


def _colorref(token: str) -> int:
    argb = _argb(token)
    return ((argb & 0xFF) << 16) | (argb & 0xFF00) | ((argb >> 16) & 0xFF)


def _asset(name: str) -> Path | None:
    """Рядом с exe в сборке, в assets репозитория при запуске из исходников."""
    exe_dir = Path(sys.executable).resolve().parent
    repo = Path(__file__).resolve().parents[2] / "assets"
    for candidate in (exe_dir / name, repo / "icons" / name, repo / "fonts" / name):
        if candidate.is_file():
            return candidate
    return None


class _RectF(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float), ("w", ctypes.c_float), ("h", ctypes.c_float)]


class _PointF(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float)]


class _StartupInput(ctypes.Structure):
    _fields_ = [
        ("version", ctypes.c_uint32),
        ("callback", ctypes.c_void_p),
        ("suppress_thread", wintypes.BOOL),
        ("suppress_codecs", wintypes.BOOL),
    ]


class _Paint(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("erase", wintypes.BOOL),
        ("rc", wintypes.RECT),
        ("restore", wintypes.BOOL),
        ("inc_update", wintypes.BOOL),
        ("reserved", ctypes.c_byte * 32),
    ]


class _WndClass(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("wndproc", ctypes.c_void_p),
        ("cls_extra", ctypes.c_int),
        ("wnd_extra", ctypes.c_int),
        ("instance", wintypes.HINSTANCE),
        ("icon", wintypes.HICON),
        ("cursor", wintypes.HANDLE),
        ("background", wintypes.HBRUSH),
        ("menu", wintypes.LPCWSTR),
        ("class_name", wintypes.LPCWSTR),
    ]


_WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
_P = ctypes.c_void_p
_F = ctypes.c_float
_user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.DefWindowProcW.restype = ctypes.c_ssize_t
_user32.CreateWindowExW.restype = wintypes.HWND
_user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, _P,
]
_user32.BeginPaint.restype = wintypes.HDC
_user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.AdjustWindowRectExForDpi.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD, wintypes.UINT]
_gdi32.CreateCompatibleDC.restype = wintypes.HDC
_gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
_gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
_gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
_gdi32.SelectObject.restype = wintypes.HGDIOBJ
_gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
_gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
_gdi32.DeleteDC.argtypes = [wintypes.HDC]
_gdi32.BitBlt.argtypes = [wintypes.HDC] + [ctypes.c_int] * 4 + [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
_kernel32.GetModuleHandleW.restype = wintypes.HMODULE
_user32.LoadImageW.restype = wintypes.HANDLE
_user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]

for _name, _args in {
    "GdiplusStartup": [ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(_StartupInput), _P],
    "GdipCreateFromHDC": [wintypes.HDC, ctypes.POINTER(_P)],
    "GdipDeleteGraphics": [_P],
    "GdipSetSmoothingMode": [_P, ctypes.c_int],
    "GdipSetTextRenderingHint": [_P, ctypes.c_int],
    "GdipSetInterpolationMode": [_P, ctypes.c_int],
    "GdipSetPixelOffsetMode": [_P, ctypes.c_int],
    "GdipScaleWorldTransform": [_P, _F, _F, ctypes.c_int],
    "GdipGraphicsClear": [_P, ctypes.c_uint32],
    "GdipCreateSolidFill": [ctypes.c_uint32, ctypes.POINTER(_P)],
    "GdipCreateLineBrush": [ctypes.POINTER(_PointF), ctypes.POINTER(_PointF), ctypes.c_uint32, ctypes.c_uint32, ctypes.c_int, ctypes.POINTER(_P)],
    "GdipSetLinePresetBlend": [_P, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(_F), ctypes.c_int],
    "GdipDeleteBrush": [_P],
    "GdipCreatePen1": [ctypes.c_uint32, _F, ctypes.c_int, ctypes.POINTER(_P)],
    "GdipDeletePen": [_P],
    "GdipCreatePath": [ctypes.c_int, ctypes.POINTER(_P)],
    "GdipAddPathArc": [_P, _F, _F, _F, _F, _F, _F],
    "GdipClosePathFigure": [_P],
    "GdipDeletePath": [_P],
    "GdipFillPath": [_P, _P, _P],
    "GdipDrawPath": [_P, _P, _P],
    "GdipDrawLine": [_P, _P, _F, _F, _F, _F],
    "GdipLoadImageFromFile": [wintypes.LPCWSTR, ctypes.POINTER(_P)],
    "GdipDrawImageRect": [_P, _P, _F, _F, _F, _F],
    "GdipNewPrivateFontCollection": [ctypes.POINTER(_P)],
    "GdipPrivateAddFontFile": [_P, wintypes.LPCWSTR],
    "GdipCreateFontFamilyFromName": [wintypes.LPCWSTR, _P, ctypes.POINTER(_P)],
    "GdipCreateFont": [_P, _F, ctypes.c_int, ctypes.c_int, ctypes.POINTER(_P)],
    "GdipCreateStringFormat": [ctypes.c_int, ctypes.c_uint16, ctypes.POINTER(_P)],
    "GdipSetStringFormatAlign": [_P, ctypes.c_int],
    "GdipSetStringFormatLineAlign": [_P, ctypes.c_int],
    "GdipSetStringFormatTrimming": [_P, ctypes.c_int],
    "GdipSetStringFormatFlags": [_P, ctypes.c_int],
    "GdipDrawString": [_P, wintypes.LPCWSTR, ctypes.c_int, _P, ctypes.POINTER(_RectF), _P, _P],
}.items():
    getattr(_gdip, _name).argtypes = _args


class _Painter:
    """GDI+ поверх буфера окна: заливки, скругления по токенам, текст Inter."""

    def __init__(self) -> None:
        token = ctypes.c_size_t()
        _gdip.GdiplusStartup(ctypes.byref(token), ctypes.byref(_StartupInput(1, None, False, False)), None)
        self._fonts: dict[tuple[bool, float], _P] = {}
        self._inter = _P()
        self._segoe = _P()
        self._collection = _P()
        _gdip.GdipNewPrivateFontCollection(ctypes.byref(self._collection))
        inter = _asset("Inter.ttf")
        if inter:
            _gdip.GdipPrivateAddFontFile(self._collection, str(inter))
        self._mark = _P()
        mark = _asset("mark-dark.png")
        if mark:
            _gdip.GdipLoadImageFromFile(str(mark), ctypes.byref(self._mark))
        self._formats: dict[tuple[int, bool], _P] = {}
        self.g = _P()

    def begin(self, hdc, scale: float) -> None:
        _gdip.GdipCreateFromHDC(hdc, ctypes.byref(self.g))
        _gdip.GdipSetSmoothingMode(self.g, 4)
        _gdip.GdipSetTextRenderingHint(self.g, 5)
        _gdip.GdipSetInterpolationMode(self.g, 7)
        _gdip.GdipSetPixelOffsetMode(self.g, 4)
        _gdip.GdipScaleWorldTransform(self.g, scale, scale, 0)

    def end(self) -> None:
        _gdip.GdipDeleteGraphics(self.g)

    def clear(self, argb: int) -> None:
        _gdip.GdipGraphicsClear(self.g, argb)

    @staticmethod
    def _rounded(x: float, y: float, w: float, h: float, r: float) -> _P:
        path = _P()
        _gdip.GdipCreatePath(0, ctypes.byref(path))
        r = max(0.01, min(r, w / 2, h / 2))
        d = 2 * r
        _gdip.GdipAddPathArc(path, x, y, d, d, 180, 90)
        _gdip.GdipAddPathArc(path, x + w - d, y, d, d, 270, 90)
        _gdip.GdipAddPathArc(path, x + w - d, y + h - d, d, d, 0, 90)
        _gdip.GdipAddPathArc(path, x, y + h - d, d, d, 90, 90)
        _gdip.GdipClosePathFigure(path)
        return path

    def fill(self, x, y, w, h, r, argb: int) -> None:
        if w <= 0:
            return
        brush = _P()
        _gdip.GdipCreateSolidFill(argb, ctypes.byref(brush))
        path = self._rounded(x, y, w, h, r)
        _gdip.GdipFillPath(self.g, brush, path)
        _gdip.GdipDeletePath(path)
        _gdip.GdipDeleteBrush(brush)

    def outline(self, x, y, w, h, r, argb: int) -> None:
        pen = _P()
        _gdip.GdipCreatePen1(argb, 1.0, 0, ctypes.byref(pen))
        path = self._rounded(x + 0.5, y + 0.5, w - 1, h - 1, r)
        _gdip.GdipDrawPath(self.g, pen, path)
        _gdip.GdipDeletePath(path)
        _gdip.GdipDeletePen(pen)

    def line(self, x1, y1, x2, y2, argb: int) -> None:
        pen = _P()
        _gdip.GdipCreatePen1(argb, 1.0, 0, ctypes.byref(pen))
        _gdip.GdipDrawLine(self.g, pen, x1, y1, x2, y2)
        _gdip.GdipDeletePen(pen)

    def gradient(self, x, y, w, h, r, stops: list[tuple[float, int]], clip=None) -> None:
        """Горизонтальный градиент по точкам; clip — скруглённая форма, в которую он вписан."""
        if w <= 0:
            return
        brush = _P()
        p1, p2 = _PointF(x, 0), _PointF(x + w, 0)
        _gdip.GdipCreateLineBrush(ctypes.byref(p1), ctypes.byref(p2), stops[0][1], stops[-1][1], 0, ctypes.byref(brush))
        colors = (ctypes.c_uint32 * len(stops))(*(c for _, c in stops))
        positions = (_F * len(stops))(*(p for p, _ in stops))
        _gdip.GdipSetLinePresetBlend(brush, colors, positions, len(stops))
        path = self._rounded(*(clip or (x, y, w, h, r)))
        _gdip.GdipFillPath(self.g, brush, path)
        _gdip.GdipDeletePath(path)
        _gdip.GdipDeleteBrush(brush)

    def mark(self, x, y, size) -> None:
        if self._mark:
            _gdip.GdipDrawImageRect(self.g, self._mark, x, y, size, size)

    def _font(self, heading: bool, size: float) -> _P:
        """Заголовок — Inter полужирным, как подписи Tigo; текст — Segoe UI, как тело Tigo."""
        key = (heading, size)
        if key not in self._fonts:
            if not self._segoe:
                _gdip.GdipCreateFontFamilyFromName("Segoe UI", None, ctypes.byref(self._segoe))
                if _gdip.GdipCreateFontFamilyFromName("Inter", self._collection, ctypes.byref(self._inter)) != 0:
                    self._inter = self._segoe
            font = _P()
            family = self._inter if heading else self._segoe
            _gdip.GdipCreateFont(family, size, 1 if heading else 0, 2, ctypes.byref(font))
            self._fonts[key] = font
        return self._fonts[key]

    def _format(self, align: int, wrap: bool) -> _P:
        key = (align, wrap)
        if key not in self._formats:
            fmt = _P()
            _gdip.GdipCreateStringFormat(0, 0, ctypes.byref(fmt))
            _gdip.GdipSetStringFormatAlign(fmt, align)
            _gdip.GdipSetStringFormatLineAlign(fmt, 0)
            _gdip.GdipSetStringFormatTrimming(fmt, 3)
            if not wrap:
                _gdip.GdipSetStringFormatFlags(fmt, 0x1000)
            self._formats[key] = fmt
        return self._formats[key]

    def text(self, value, x, y, w, h, *, size, argb, heading=False, align=0, wrap=False) -> None:
        brush = _P()
        _gdip.GdipCreateSolidFill(argb, ctypes.byref(brush))
        rect = _RectF(x, y, w, h)
        _gdip.GdipDrawString(
            self.g, value, -1, self._font(heading, size), ctypes.byref(rect), self._format(align, wrap), brush
        )
        _gdip.GdipDeleteBrush(brush)


class UpdateWindow:
    def __init__(self, worker: Worker) -> None:
        self.worker = worker
        self.painter = _Painter()
        self.started = time.monotonic()
        self.done_at = 0.0
        self.hover_close = False
        self.scale = 1.0
        self.hwnd = None
        self._proc = _WNDPROC(self._wndproc)

    def _close_rect(self) -> tuple[float, float, float, float]:
        w, h = 104, px("size-control-sm")
        return _W - _PAD - w, _H - _PAD - h, w, h

    def _in_close(self, x: float, y: float) -> bool:
        if self.worker.snapshot().stage != "error":
            return False
        cx, cy, cw, ch = self._close_rect()
        return cx <= x <= cx + cw and cy <= y <= cy + ch

    def _client_point(self, lparam) -> tuple[float, float]:
        x = ctypes.c_short(lparam & 0xFFFF).value
        y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
        return x / self.scale, y / self.scale

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == _WM_MOUSEMOVE:
            self.hover_close = self._in_close(*self._client_point(lparam))
            return 0
        if msg == _WM_LBUTTONUP:
            if self._in_close(*self._client_point(lparam)):
                _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
            return 0
        if msg == _WM_TIMER:
            state = self.worker.snapshot()
            if state.stage == "done":
                self.done_at = self.done_at or time.monotonic()
                if time.monotonic() - self.done_at >= _CLOSE_AFTER_DONE_S:
                    _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
            _user32.InvalidateRect(hwnd, None, False)
            return 0
        if msg == _WM_ERASEBKGND:
            return 1
        if msg == _WM_PAINT:
            self._paint(hwnd)
            return 0
        if msg == _WM_DESTROY:
            _user32.PostQuitMessage(0)
            return 0
        return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _paint(self, hwnd) -> None:
        ps = _Paint()
        hdc = _user32.BeginPaint(hwnd, ctypes.byref(ps))
        width, height = round(_W * self.scale), round(_H * self.scale)
        mem = _gdi32.CreateCompatibleDC(hdc)
        bitmap = _gdi32.CreateCompatibleBitmap(hdc, width, height)
        old = _gdi32.SelectObject(mem, bitmap)
        p = self.painter
        p.begin(mem, self.scale)
        self._draw(p, self.worker.snapshot())
        p.end()
        _gdi32.BitBlt(hdc, 0, 0, width, height, mem, 0, 0, _SRCCOPY)
        _gdi32.SelectObject(mem, old)
        _gdi32.DeleteObject(bitmap)
        _gdi32.DeleteDC(mem)
        _user32.EndPaint(hwnd, ctypes.byref(ps))

    def _draw(self, p: _Painter, s: State) -> None:
        job = self.worker.job
        error = s.stage == "error"
        accent = "feedback-error-text" if error else "action-primary"
        p.clear(_argb("surface-page"))

        # Шапка: знак в хроме, новая версия и с какой обновляемся.
        p.mark(_PAD - 4, _PAD - 4, 40)
        p.text(f"Tigo {job.version}", 72, _PAD - 1, 300, 22, size=px("text-base"), argb=_argb("text-primary"), heading=True)
        if job.from_version:
            p.text(f"Обновление с версии {job.from_version}", 72, _PAD + 20, 300, 18, size=12, argb=_argb("text-tertiary"))

        # Подпись этапа и процент.
        top = 88
        p.text(s.caption, _PAD, top, _W - 2 * _PAD - 60, 20, size=14, argb=_argb(accent if error else "text-primary"), heading=True)
        if s.progress is not None and s.stage in {"download", "verify", "install"}:
            p.text(f"{math.floor(s.progress * 100)}%", _W - _PAD - 60, top, 60, 20, size=14, argb=_argb(accent), heading=True, align=2)

        # Шкала: дорожка, заливка с градиентом акцента и бегущий блеск рельса.
        bar_y, bar_h, bar_w = top + 28, 6, _W - 2 * _PAD
        radius = px("radius-xs")
        p.fill(_PAD, bar_y, bar_w, bar_h, radius, _argb("border-default"))
        t = time.monotonic() - self.started
        if s.stage == "done":
            fill_x, fill_w = _PAD, bar_w
        elif s.progress is None and not error:
            span = bar_w * 0.28
            head = _PAD - span + (bar_w + span) * ((t % 1.6) / 1.6)
            fill_x = max(head, _PAD)
            fill_w = min(head + span, _PAD + bar_w) - fill_x
        else:
            fill_x, fill_w = _PAD, bar_w * (s.progress if s.progress is not None else 1.0)
        if fill_w > 0:
            base = "feedback-error-text" if error else "action-primary-active"
            p.gradient(fill_x, bar_y, fill_w, bar_h, radius, [(0.0, _argb(base)), (1.0, _argb(accent))])
            if not error:
                sheen = bar_w * 0.22
                pos = ((t % _BAR_SHEEN_PERIOD_S) / _BAR_SHEEN_PERIOD_S) * (bar_w + 2 * sheen) - sheen + _PAD
                glow = _argb("umbrae-rail-sheen")
                clear = glow & 0x00FFFFFF
                p.gradient(
                    pos, bar_y, sheen, bar_h, radius,
                    [(0.0, clear), (0.5, glow), (1.0, clear)],
                    clip=(fill_x, bar_y, fill_w, bar_h, radius),
                )

        # Подробности под шкалой; в ошибке — причина и кнопка «Закрыть».
        detail_y = bar_y + bar_h + 10
        if error:
            p.text(s.detail, _PAD, detail_y, _W - 2 * _PAD, 38, size=14, argb=_argb("text-secondary"), wrap=True)
        elif s.detail:
            p.text(s.detail, _PAD, detail_y, _W - 2 * _PAD, 18, size=12, argb=_argb("text-tertiary"))

        # Короткий лог: последние строки, свежая ярче.
        log_top = detail_y + (46 if error else 30)
        p.line(_PAD, log_top - 8, _W - _PAD, log_top - 8, _argb("border-default"))
        lines = s.log[-(2 if error else 4) :]
        for i, entry in enumerate(lines):
            color = "text-secondary" if i == len(lines) - 1 else "text-disabled"
            p.text(entry, _PAD, log_top + i * 17, _W - 2 * _PAD - (112 if error else 0), 17, size=12, argb=_argb(color))

        if error:
            x, y, w, h = self._close_rect()
            radius = px("radius-button")
            if self.hover_close:
                p.fill(x, y, w, h, radius, _argb("button-secondary-bg-hover"))
            p.outline(x, y, w, h, radius, _argb("button-secondary-border"))
            p.text("Закрыть", x, y + (h - 19) / 2, w, 20, size=14, argb=_argb("button-secondary-text"), heading=True, align=1)

    def run(self) -> None:
        _user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        self.scale = _user32.GetDpiForSystem() / 96
        instance = _kernel32.GetModuleHandleW(None)
        wndclass = _WndClass()
        wndclass.wndproc = ctypes.cast(self._proc, ctypes.c_void_p)
        wndclass.instance = instance
        wndclass.cursor = _user32.LoadCursorW(None, 32512)
        wndclass.class_name = "TigoUpdate"
        _user32.RegisterClassW(ctypes.byref(wndclass))

        style = _WS_CAPTION | _WS_SYSMENU | _WS_MINIMIZEBOX
        frame = wintypes.RECT(0, 0, round(_W * self.scale), round(_H * self.scale))
        _user32.AdjustWindowRectExForDpi(ctypes.byref(frame), style, False, 0, round(self.scale * 96))
        width, height = frame.right - frame.left, frame.bottom - frame.top
        x = max(0, (_user32.GetSystemMetrics(0) - width) // 2)
        y = max(0, (_user32.GetSystemMetrics(1) - height) // 2)
        self.hwnd = _user32.CreateWindowExW(
            0, "TigoUpdate", "Обновление Tigo", style, x, y, width, height, None, None, instance, None,
        )
        if not self.hwnd:
            raise OSError(f"CreateWindowExW: {ctypes.get_last_error()}")
        self._style_frame()
        self._set_icon()
        _user32.ShowWindow(self.hwnd, 5)
        _user32.SetForegroundWindow(self.hwnd)
        _user32.SetTimer(self.hwnd, 1, _FRAME_MS, None)
        self.worker.start()

        msg = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

    def _set_icon(self) -> None:
        """Значок рамки и панели задач из app.ico рядом с exe, в обоих размерах для текущего DPI."""
        ico = _asset("app.ico")
        if ico is None:
            return
        dpi = round(self.scale * 96)
        for kind, metric in ((0, 49), (1, 11)):  # ICON_SMALL: SM_CXSMICON, ICON_BIG: SM_CXICON
            size = _user32.GetSystemMetricsForDpi(metric, dpi)
            icon = _user32.LoadImageW(None, str(ico), 1, size, size, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
            if icon:
                _user32.SendMessageW(self.hwnd, _WM_SETICON, kind, icon)

    def _style_frame(self) -> None:
        """Рамка Windows в тёмной теме: заголовок цвета фона, обводка цвета карточки."""
        def attr(key: int, value: int) -> None:
            data = ctypes.c_int(value)
            _dwmapi.DwmSetWindowAttribute(self.hwnd, key, ctypes.byref(data), ctypes.sizeof(data))

        attr(20, 1)  # DWMWA_USE_IMMERSIVE_DARK_MODE
        attr(34, _colorref("card-border"))  # DWMWA_BORDER_COLOR
        attr(35, _colorref("surface-page"))  # DWMWA_CAPTION_COLOR
        attr(36, _colorref("text-secondary"))  # DWMWA_TEXT_COLOR


def run_update_window(worker: Worker) -> None:
    UpdateWindow(worker).run()
