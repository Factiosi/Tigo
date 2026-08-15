"""Set human-readable process description visible in Task Manager."""

from __future__ import annotations

import sys


def set_process_description(label: str) -> None:
    if sys.platform != "win32" or not label.strip():
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernelbase = ctypes.WinDLL("kernelbase", use_last_error=True)
        set_desc = getattr(kernelbase, "SetProcessDescription", None)
        if set_desc is None:
            return

        set_desc.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR]
        set_desc.restype = wintypes.HRESULT
        process = ctypes.windll.kernel32.GetCurrentProcess()
        set_desc(process, label.strip())
    except (AttributeError, OSError, TypeError, ValueError):
        pass
