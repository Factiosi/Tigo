"""Lightweight pub/sub between modules."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Callable

_lock = threading.RLock()
_subscribers: dict[str, list[Callable[..., None]]] = defaultdict(list)


def subscribe(event: str, handler: Callable[..., None]) -> None:
    with _lock:
        _subscribers[event].append(handler)


def unsubscribe(event: str, handler: Callable[..., None]) -> None:
    with _lock:
        handlers = _subscribers.get(event)
        if handlers and handler in handlers:
            handlers.remove(handler)


def emit(event: str, *args: Any, **kwargs: Any) -> None:
    with _lock:
        handlers = list(_subscribers.get(event, []))
    for handler in handlers:
        try:
            handler(*args, **kwargs)
        except Exception:
            pass
