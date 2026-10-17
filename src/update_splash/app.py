"""Win32 progress window for TigoUpdate.exe."""

from __future__ import annotations

import socket
import sys
import time

from src.core.paths import APP_NAME
from src.modules.updates.splash_status import read_update_status

if sys.platform != "win32":
    raise RuntimeError("Update splash is only supported on Windows.")

import ctypes
from ctypes import wintypes

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_gdi32 = ctypes.windll.gdi32

_WS_OVERLAPPEDWINDOW = 0x00CF0000
_WS_VISIBLE = 0x10000000
_SW_SHOW = 5
_WM_DESTROY = 0x0002
_WM_CLOSE = 0x0010
_WM_TIMER = 0x0113
_WM_PAINT = 0x000F
_WM_SETFONT = 0x0030
_ID_TIMER = 1
_ID_STATIC = 1001
_TIMEOUT_MS = 45 * 60 * 1000
_FAIL_CLOSE_MS = 6000
_DAEMON_PORT = 51731


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


_WNDPROC = ctypes.WINFUNCTYPE(
    wintypes.LPARAM,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


def _daemon_reachable() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", _DAEMON_PORT), timeout=0.4):
            return True
    except OSError:
        return False


def run_update_splash() -> None:
    state = {
        "text": f"Обновление {APP_NAME}...",
        "phase": "checking",
        "fail_deadline": 0.0,
        "started": time.monotonic(),
    }
    static_hwnd = wintypes.HWND(0)
    font = _gdi32.CreateFontW(
        20,
        0,
        0,
        0,
        400,
        0,
        0,
        0,
        204,
        0,
        0,
        0,
        0,
        "Segoe UI",
    )

    @_WNDPROC
    def wnd_proc(hwnd, msg, wparam, lparam):
        nonlocal static_hwnd
        if msg == _WM_TIMER:
            payload = read_update_status()
            phase = str(payload.get("phase") or state["phase"])
            message = str(payload.get("message") or state["text"]).strip()
            if message:
                state["text"] = message
            state["phase"] = phase
            if static_hwnd:
                _user32.SetWindowTextW(static_hwnd, state["text"])
            if phase == "done":
                _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
            elif phase == "failed":
                if state["fail_deadline"] <= 0:
                    state["fail_deadline"] = time.monotonic() + (_FAIL_CLOSE_MS / 1000)
                elif time.monotonic() >= state["fail_deadline"]:
                    _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
            elif phase == "restarting" and _daemon_reachable():
                _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
            elif (time.monotonic() - state["started"]) * 1000 >= _TIMEOUT_MS:
                _user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
            return 0
        if msg == _WM_DESTROY:
            _user32.PostQuitMessage(0)
            return 0
        return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    class_name = "TigoUpdateSplash"
    hinstance = _kernel32.GetModuleHandleW(None)
    wndclass = WNDCLASSW()
    wndclass.lpfnWndProc = wnd_proc
    wndclass.hInstance = hinstance
    wndclass.hCursor = _user32.LoadCursorW(None, 32512)
    wndclass.hbrBackground = _gdi32.GetStockObject(4)
    wndclass.lpszClassName = class_name
    if not _user32.RegisterClassW(ctypes.byref(wndclass)):
        raise OSError("RegisterClassW failed")

    width, height = 520, 180
    screen_w = _user32.GetSystemMetrics(0)
    screen_h = _user32.GetSystemMetrics(1)
    x = max(0, (screen_w - width) // 2)
    y = max(0, (screen_h - height) // 2)
    hwnd = _user32.CreateWindowExW(
        0,
        class_name,
        APP_NAME,
        _WS_OVERLAPPEDWINDOW | _WS_VISIBLE,
        x,
        y,
        width,
        height,
        None,
        None,
        hinstance,
        None,
    )
    if not hwnd:
        raise OSError("CreateWindowExW failed")

    static_hwnd = _user32.CreateWindowExW(
        0,
        "Static",
        state["text"],
        0x50000000,
        24,
        48,
        width - 48,
        height - 72,
        hwnd,
        _ID_STATIC,
        hinstance,
        None,
    )
    if static_hwnd and font:
        _user32.SendMessageW(static_hwnd, _WM_SETFONT, font, 1)

    _user32.SetTimer(hwnd, _ID_TIMER, 400, None)
    _user32.ShowWindow(hwnd, _SW_SHOW)
    _user32.UpdateWindow(hwnd)

    msg = wintypes.MSG()
    while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        _user32.TranslateMessage(ctypes.byref(msg))
        _user32.DispatchMessageW(ctypes.byref(msg))
