from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.modules.lifecycle.public import start_daemon_watchdog


class DaemonWatchdogTests(unittest.IsolatedAsyncioTestCase):
    async def test_watchdog_closes_gui_when_daemon_stops(self) -> None:
        page = MagicMock()
        page.on_disconnect = None
        page.window.destroy = AsyncMock()
        checks = iter([True, False])

        def running() -> bool:
            return next(checks, False)

        with patch("src.daemon.ipc.is_daemon_running", side_effect=running):
            start_daemon_watchdog(page, interval=0.01)
            watch = page.run_task.call_args.args[0]
            await watch()

        page.window.destroy.assert_awaited_once()

    async def test_watchdog_stops_after_disconnect(self) -> None:
        page = MagicMock()
        page.on_disconnect = None
        page.window.destroy = AsyncMock()

        with patch("src.daemon.ipc.is_daemon_running", return_value=True):
            start_daemon_watchdog(page, interval=0.01)
            watch = page.run_task.call_args.args[0]
            page.on_disconnect(None)
            await asyncio.wait_for(watch(), timeout=0.2)

        page.window.destroy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
