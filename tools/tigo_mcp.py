"""Local stdio MCP server for development and explicitly enabled Tigo builds."""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server import MCPServer

from src.daemon.ipc import (
    daemon_automation_info,
    daemon_get_settings,
    daemon_list_strategies,
    daemon_read_log,
    daemon_start,
    daemon_status,
    daemon_stop,
    daemon_test_start,
    daemon_test_status,
    daemon_test_stop,
    daemon_update_settings,
    daemon_update_strategies,
    is_daemon_running,
)

mcp = MCPServer(
    "tigo-automation",
    title="Tigo Automation",
    description="Local development controls for the Tigo daemon.",
    instructions=(
        "Operate only the local Tigo instance. Extended tools require a source "
        "daemon or a packaged daemon started with TIGO_AUTOMATION=1."
    ),
)


@mcp.tool()
def tigo_ping() -> dict[str, Any]:
    """Check whether the local Tigo daemon is reachable and automation is enabled."""
    return {
        "ok": is_daemon_running(),
        "automation": daemon_automation_info(),
    }


@mcp.tool()
def tigo_status() -> dict[str, Any]:
    """Return current winws and strategy-test runtime status."""
    status = daemon_status()
    if status is None:
        return {"ok": False, "error": "Tigo daemon недоступен."}
    return {"ok": True, "status": asdict(status)}


@mcp.tool()
def tigo_start() -> dict[str, Any]:
    """Start winws with the strategy selected in Tigo settings."""
    ok, message = daemon_start()
    return {"ok": ok, "message": message}


@mcp.tool()
def tigo_stop() -> dict[str, Any]:
    """Stop the winws process owned by the Tigo daemon."""
    ok, message = daemon_stop()
    return {"ok": ok, "message": message}


@mcp.tool()
def tigo_list_strategies() -> dict[str, Any]:
    """List installed Flowseal strategies and the selected strategy."""
    return daemon_list_strategies()


@mcp.tool()
def tigo_start_tests(
    version: str,
    strategy_ids: list[str],
    test_type: str = "standard",
) -> dict[str, Any]:
    """Start daemon-owned strategy tests for explicit strategy IDs."""
    ok, message = daemon_test_start(version, test_type, strategy_ids)
    return {"ok": ok, "message": message}


@mcp.tool()
def tigo_test_status() -> dict[str, Any]:
    """Return strategy-test progress and current strategy ID."""
    return daemon_test_status()


@mcp.tool()
def tigo_stop_tests() -> dict[str, Any]:
    """Request cancellation of the active strategy-test run."""
    ok, message = daemon_test_stop()
    return {"ok": ok, "message": message}


@mcp.tool()
def tigo_get_settings() -> dict[str, Any]:
    """Return current Tigo settings from the daemon process."""
    return daemon_get_settings()


@mcp.tool()
def tigo_update_settings(values: dict[str, Any]) -> dict[str, Any]:
    """Update validated Tigo settings; storage_root is intentionally excluded."""
    return daemon_update_settings(values)


@mcp.tool()
def tigo_read_debug_log(limit: int = 100) -> dict[str, Any]:
    """Read the latest Tigo debug-log lines, up to 500."""
    return daemon_read_log(limit)


@mcp.tool()
def tigo_update_strategies() -> dict[str, Any]:
    """Check, download, apply and, when needed, restart Flowseal strategies."""
    return daemon_update_strategies()


if __name__ == "__main__":
    mcp.run(transport="stdio")
