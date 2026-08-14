"""Localhost JSON IPC between Z1UI GUI and daemon."""

from __future__ import annotations

import json
import socket
import threading
from typing import Any, Callable

from src.core.debug_log import debug
from src.daemon.protocol import CommandName, DaemonStatus, status_from_dict, status_to_dict

HOST = "127.0.0.1"
PORT = 51731
_TIMEOUT = 2.0


def _send_recv(payload: dict[str, Any]) -> dict[str, Any]:
    data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=_TIMEOUT) as sock:
        sock.sendall(data)
        sock.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        while True:
            part = sock.recv(4096)
            if not part:
                break
            chunks.append(part)
    raw = b"".join(chunks).decode("utf-8").strip()
    if not raw:
        return {"ok": False, "error": "Пустой ответ daemon."}
    return json.loads(raw)


def is_daemon_running() -> bool:
    try:
        response = _send_recv({"cmd": "ping"})
        return bool(response.get("ok"))
    except OSError:
        return False


def daemon_status() -> DaemonStatus | None:
    try:
        response = _send_recv({"cmd": "status"})
        if not response.get("ok"):
            return None
        return status_from_dict(response.get("status") or {})
    except OSError:
        return None


def daemon_start() -> tuple[bool, str]:
    try:
        response = _send_recv({"cmd": "start"})
        return bool(response.get("ok")), str(response.get("message") or response.get("error") or "")
    except OSError as exc:
        return False, str(exc)


def daemon_stop() -> tuple[bool, str]:
    try:
        response = _send_recv({"cmd": "stop"})
        return bool(response.get("ok")), str(response.get("message") or response.get("error") or "")
    except OSError as exc:
        return False, str(exc)


def daemon_open_ui() -> tuple[bool, str]:
    try:
        response = _send_recv({"cmd": "open_ui"})
        return bool(response.get("ok")), str(response.get("message") or response.get("error") or "")
    except OSError as exc:
        return False, str(exc)


def daemon_shutdown() -> tuple[bool, str]:
    try:
        response = _send_recv({"cmd": "shutdown"})
        return bool(response.get("ok")), str(response.get("message") or response.get("error") or "")
    except OSError as exc:
        return False, str(exc)


def register_gui_with_daemon(pid: int | None = None) -> None:
    payload: dict[str, Any] = {"cmd": "register_gui"}
    if pid is not None:
        payload["pid"] = pid
    try:
        _send_recv(payload)
    except OSError:
        pass


class IpcServer:
    def __init__(self, handler: Callable[[CommandName, dict[str, Any]], dict[str, Any]]) -> None:
        self._handler = handler
        self._thread: threading.Thread | None = None
        self._running = False
        self._sock: socket.socket | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True, name="z1ui-ipc")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def _serve(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(5)
        server.settimeout(1.0)
        self._sock = server
        debug("daemon", f"IPC listening on {HOST}:{PORT}")
        while self._running:
            try:
                conn, _addr = server.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn: socket.socket) -> None:
        try:
            chunks: list[bytes] = []
            while True:
                part = conn.recv(4096)
                if not part:
                    break
                chunks.append(part)
            raw = b"".join(chunks).decode("utf-8").strip()
            if not raw:
                conn.sendall(b'{"ok": false, "error": "empty request"}\n')
                return
            request = json.loads(raw)
            cmd = str(request.get("cmd") or "ping")
            response = self._handler(cmd, request)  # type: ignore[arg-type]
            conn.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            try:
                conn.sendall(
                    (json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False) + "\n").encode("utf-8")
                )
            except OSError:
                pass
        finally:
            conn.close()


def build_status_response() -> dict[str, Any]:
    from src.kernel.public import get_runtime_status

    status = get_runtime_status()
    payload = status_to_dict(
        DaemonStatus(
            running=status.running,
            phase=status.phase.value,
            strategy_name=status.strategy_name or "",
            error=status.error or "",
            pid=status.pid,
        )
    )
    return {"ok": True, "status": payload}
