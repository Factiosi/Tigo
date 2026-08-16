"""Set human-readable process description visible in Task Manager."""

from __future__ import annotations

import os
import sys

_PROCESS_SET_LIMITED_INFORMATION = 0x0002_0000
_TH32CS_SNAPPROCESS = 0x0000_0002
_MAX_PATH = 260


def _apply_process_description(process_handle: int, label: str) -> bool:
    import ctypes
    from ctypes import wintypes

    kernelbase = ctypes.WinDLL("kernelbase", use_last_error=True)
    set_desc = getattr(kernelbase, "SetProcessDescription", None)
    if set_desc is None:
        return False

    set_desc.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR]
    set_desc.restype = wintypes.HRESULT
    result = set_desc(process_handle, label.strip())
    return result == 0


def set_process_description(label: str) -> None:
    if sys.platform != "win32" or not label.strip():
        return
    try:
        import ctypes

        process = ctypes.windll.kernel32.GetCurrentProcess()
        _apply_process_description(process, label)
    except (AttributeError, OSError, TypeError, ValueError):
        pass


def set_process_description_for_pid(pid: int, label: str) -> bool:
    if sys.platform != "win32" or pid <= 0 or not label.strip():
        return False
    try:
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(_PROCESS_SET_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            return _apply_process_description(handle, label)
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def _iter_child_processes(parent_pid: int) -> list[tuple[int, str]]:
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * _MAX_PATH),
        ]

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if snapshot in (-1, 0):
        return []

    entries: list[tuple[int, str]] = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return []
        while True:
            if entry.th32ParentProcessID == parent_pid:
                entries.append((entry.th32ProcessID, entry.szExeFile))
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return entries


def label_flet_view_process(label: str, *, parent_pid: int | None = None) -> bool:
    """Rename the spawned flet.exe client visible as the parent row in Task Manager."""
    if sys.platform != "win32" or not label.strip():
        return False
    parent = parent_pid if parent_pid is not None else os.getpid()
    labeled = False
    for pid, exe_name in _iter_child_processes(parent):
        if exe_name.casefold() == "flet.exe":
            labeled = set_process_description_for_pid(pid, label) or labeled
    return labeled
