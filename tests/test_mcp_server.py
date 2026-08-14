from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from mcp import Client

from src.core.automation import automation_enabled
from tools.tigo_mcp import mcp


class AutomationGuardTests(unittest.TestCase):
    def test_source_runs_enable_automation(self) -> None:
        with patch("src.core.automation.is_packaged_app", return_value=False):
            self.assertTrue(automation_enabled())

    def test_packaged_runs_require_explicit_flag(self) -> None:
        with (
            patch("src.core.automation.is_packaged_app", return_value=True),
            patch.dict(os.environ, {}, clear=True),
        ):
            self.assertFalse(automation_enabled())
        with (
            patch("src.core.automation.is_packaged_app", return_value=True),
            patch.dict(os.environ, {"TIGO_AUTOMATION": "1"}, clear=True),
        ):
            self.assertTrue(automation_enabled())


class McpSurfaceTests(unittest.TestCase):
    def test_expected_tools_are_registered(self) -> None:
        names = {tool.name for tool in mcp._tool_manager.list_tools()}  # noqa: SLF001
        self.assertEqual(
            names,
            {
                "tigo_ping",
                "tigo_status",
                "tigo_start",
                "tigo_stop",
                "tigo_list_strategies",
                "tigo_start_tests",
                "tigo_test_status",
                "tigo_stop_tests",
                "tigo_get_settings",
                "tigo_update_settings",
                "tigo_read_debug_log",
                "tigo_update_strategies",
            },
        )


class McpCallTests(unittest.IsolatedAsyncioTestCase):
    async def test_ping_tool_runs_through_mcp_protocol(self) -> None:
        with (
            patch("tools.tigo_mcp.is_daemon_running", return_value=True),
            patch(
                "tools.tigo_mcp.daemon_automation_info",
                return_value={"ok": True, "enabled": True, "packaged": False},
            ),
        ):
            async with Client(mcp) as client:
                result = await client.call_tool("tigo_ping", {})
        self.assertEqual(result.structured_content["ok"], True)


if __name__ == "__main__":
    unittest.main()
