"""Lightweight winws process probe (canonical path)."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path

from src.core.paths import bin_dir

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MAX_PATH = 32768


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def _normalize_path(path: str) -> str:
    text = str(path or "").strip()
    if text.startswith("\\\\?\\"):
        text = text[4:]
    try:
        text = os.path.abspath(text)
    except OSError:
        pass
    return os.path.normcase(text)


def expected_winws_path() -> Path:
    return (bin_dir() / "winws.exe").resolve()


def _query_image_path(pid: int) -> str:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(MAX_PATH)
        size = wintypes.DWORD(len(buf))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return ""
        return _normalize_path(buf.value)
    finally:
        kernel32.CloseHandle(handle)


def find_canonical_winws_pids() -> list[int]:
    expected = _normalize_path(str(expected_winws_path()))
    if not expected:
        return []

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot in (-1, 0xFFFFFFFF):
        return []

    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    pids: list[int] = []

    try:
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return []
        while True:
            name = entry.szExeFile.lower()
            if name == "winws.exe":
                pid = int(entry.th32ProcessID)
                image = _query_image_path(pid)
                if image == expected:
                    pids.append(pid)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)

    return pids


def is_canonical_winws_running() -> tuple[bool, int | None]:
    pids = find_canonical_winws_pids()
    if not pids:
        return False, None
    return True, pids[0]
