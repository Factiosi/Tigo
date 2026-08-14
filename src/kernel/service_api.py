"""Windows Service Control Manager via Win32 API (avoids sc.exe quoting bugs)."""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from typing import Optional

advapi32 = ctypes.windll.advapi32
kernel32 = ctypes.windll.kernel32

SC_MANAGER_ALL_ACCESS = 0xF003F
SC_MANAGER_CREATE_SERVICE = 0x0002
SC_MANAGER_CONNECT = 0x0001

SERVICE_ALL_ACCESS = 0xF01FF
SERVICE_START = 0x0010
SERVICE_STOP = 0x0020
SERVICE_QUERY_STATUS = 0x0004
DELETE = 0x00010000

SERVICE_WIN32_OWN_PROCESS = 0x00000010
SERVICE_AUTO_START = 0x00000002
SERVICE_ERROR_NORMAL = 0x00000001

SERVICE_CONTROL_STOP = 0x00000001
SERVICE_STOPPED = 0x00000001
SERVICE_RUNNING = 0x00000004

SERVICE_CONFIG_DESCRIPTION = 1


class SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ("dwServiceType", wintypes.DWORD),
        ("dwCurrentState", wintypes.DWORD),
        ("dwControlsAccepted", wintypes.DWORD),
        ("dwWin32ExitCode", wintypes.DWORD),
        ("dwServiceSpecificExitCode", wintypes.DWORD),
        ("dwCheckPoint", wintypes.DWORD),
        ("dwWaitHint", wintypes.DWORD),
    ]


class SERVICE_DESCRIPTION(ctypes.Structure):
    _fields_ = [("lpDescription", wintypes.LPWSTR)]


advapi32.OpenSCManagerW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
advapi32.OpenSCManagerW.restype = wintypes.HANDLE
advapi32.CloseServiceHandle.argtypes = [wintypes.HANDLE]
advapi32.CloseServiceHandle.restype = wintypes.BOOL
advapi32.CreateServiceW.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPDWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
]
advapi32.CreateServiceW.restype = wintypes.HANDLE
advapi32.OpenServiceW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, wintypes.DWORD]
advapi32.OpenServiceW.restype = wintypes.HANDLE
advapi32.DeleteService.argtypes = [wintypes.HANDLE]
advapi32.DeleteService.restype = wintypes.BOOL
advapi32.StartServiceW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.LPCWSTR)]
advapi32.StartServiceW.restype = wintypes.BOOL
advapi32.ControlService.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(SERVICE_STATUS)]
advapi32.ControlService.restype = wintypes.BOOL
advapi32.QueryServiceStatus.argtypes = [wintypes.HANDLE, ctypes.POINTER(SERVICE_STATUS)]
advapi32.QueryServiceStatus.restype = wintypes.BOOL
advapi32.ChangeServiceConfig2W.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p]
advapi32.ChangeServiceConfig2W.restype = wintypes.BOOL


def _last_error_message() -> str:
    code = kernel32.GetLastError()
    buf = ctypes.create_unicode_buffer(512)
    kernel32.FormatMessageW(0x00001300, None, code, 0, buf, len(buf), None)
    text = buf.value.strip() or f"Win32 error {code}"
    return f"{text} ({code})"


def _open_sc_manager(access: int) -> Optional[int]:
    handle = advapi32.OpenSCManagerW(None, None, access)
    return handle or None


def _close(handle: int | None) -> None:
    if handle:
        advapi32.CloseServiceHandle(handle)


def service_state(service_name: str) -> int | None:
    scm = _open_sc_manager(SC_MANAGER_CONNECT)
    if not scm:
        return None
    try:
        svc = advapi32.OpenServiceW(scm, service_name, SERVICE_QUERY_STATUS)
        if not svc:
            return None
        try:
            status = SERVICE_STATUS()
            if not advapi32.QueryServiceStatus(svc, ctypes.byref(status)):
                return None
            return int(status.dwCurrentState)
        finally:
            _close(svc)
    finally:
        _close(scm)


def stop_service(service_name: str, *, wait_timeout_ms: int = 10000) -> tuple[bool, str]:
    scm = _open_sc_manager(SC_MANAGER_CONNECT)
    if not scm:
        return False, _last_error_message()

    try:
        svc = advapi32.OpenServiceW(scm, service_name, SERVICE_STOP | SERVICE_QUERY_STATUS)
        if not svc:
            err = kernel32.GetLastError()
            if err == 1060:
                return True, "Служба не установлена."
            return False, _last_error_message()

        try:
            status = SERVICE_STATUS()
            if advapi32.QueryServiceStatus(svc, ctypes.byref(status)):
                if status.dwCurrentState == SERVICE_STOPPED:
                    return True, "Служба уже остановлена."

            if not advapi32.ControlService(svc, SERVICE_CONTROL_STOP, ctypes.byref(status)):
                err = kernel32.GetLastError()
                if err == 1062:
                    return True, "Служба не активна."
                return False, _last_error_message()

            deadline = time.time() + wait_timeout_ms / 1000
            while time.time() < deadline:
                if advapi32.QueryServiceStatus(svc, ctypes.byref(status)):
                    if status.dwCurrentState == SERVICE_STOPPED:
                        return True, "Служба остановлена."
                time.sleep(0.1)
            return False, "Таймаут остановки службы."
        finally:
            _close(svc)
    finally:
        _close(scm)


def delete_service(service_name: str) -> tuple[bool, str]:
    stop_service(service_name)
    scm = _open_sc_manager(SC_MANAGER_ALL_ACCESS)
    if not scm:
        return False, _last_error_message()

    try:
        svc = advapi32.OpenServiceW(scm, service_name, DELETE)
        if not svc:
            err = kernel32.GetLastError()
            if err == 1060:
                return True, "Служба не установлена."
            return False, _last_error_message()

        try:
            if advapi32.DeleteService(svc):
                return True, "Служба удалена."
            err = kernel32.GetLastError()
            if err == 1072:
                return True, "Служба помечена на удаление."
            return False, _last_error_message()
        finally:
            _close(svc)
    finally:
        _close(scm)


def create_service(
    service_name: str,
    *,
    display_name: str,
    binary_path: str,
    description: str | None = None,
) -> tuple[bool, str]:
    scm = _open_sc_manager(SC_MANAGER_CREATE_SERVICE)
    if not scm:
        return False, _last_error_message()

    try:
        svc = advapi32.CreateServiceW(
            scm,
            service_name,
            display_name,
            SERVICE_ALL_ACCESS,
            SERVICE_WIN32_OWN_PROCESS,
            SERVICE_AUTO_START,
            SERVICE_ERROR_NORMAL,
            binary_path,
            None,
            None,
            None,
            None,
            None,
        )
        if not svc:
            return False, _last_error_message()

        try:
            if description:
                desc = SERVICE_DESCRIPTION(lpDescription=description)
                advapi32.ChangeServiceConfig2W(
                    svc,
                    SERVICE_CONFIG_DESCRIPTION,
                    ctypes.byref(desc),
                )
            return True, "Служба создана."
        finally:
            _close(svc)
    finally:
        _close(scm)


def start_service(service_name: str) -> tuple[bool, str]:
    scm = _open_sc_manager(SC_MANAGER_CONNECT)
    if not scm:
        return False, _last_error_message()

    try:
        svc = advapi32.OpenServiceW(scm, service_name, SERVICE_START | SERVICE_QUERY_STATUS)
        if not svc:
            return False, _last_error_message()

        try:
            status = SERVICE_STATUS()
            if advapi32.QueryServiceStatus(svc, ctypes.byref(status)):
                if status.dwCurrentState == SERVICE_RUNNING:
                    return True, "Служба уже запущена."

            if advapi32.StartServiceW(svc, 0, None):
                return True, "Служба запущена."

            err = kernel32.GetLastError()
            if err == 1056:
                return True, "Служба уже запущена."
            return False, _last_error_message()
        finally:
            _close(svc)
    finally:
        _close(scm)
