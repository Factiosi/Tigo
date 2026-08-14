"""One-shot IPC ping for smoke tests."""
import json
import socket
import sys

HOST, PORT = "127.0.0.1", 51731
try:
    with socket.create_connection((HOST, PORT), timeout=3) as sock:
        sock.sendall(b'{"cmd":"ping"}\n')
        sock.shutdown(socket.SHUT_WR)
        raw = sock.recv(4096).decode("utf-8").strip()
    data = json.loads(raw)
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0 if data.get("ok") else 1)
except OSError as exc:
    print(f"IPC error: {exc}", file=sys.stderr)
    sys.exit(1)
