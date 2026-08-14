"""Persistent on-disk cache for strategy test results (per flowseal version)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.debug_log import debug, warn
from src.core.paths import test_results_cache_path
from src.modules.strategy_testing.probe import TargetProbeResult

_CACHE_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_cache_file() -> dict[str, Any]:
    path = test_results_cache_path()
    if not path.exists():
        return {"schema": _CACHE_VERSION, "versions": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warn("strategy_testing", f"test results cache unreadable: {exc}")
        return {"schema": _CACHE_VERSION, "versions": {}}
    if not isinstance(raw, dict):
        return {"schema": _CACHE_VERSION, "versions": {}}
    versions = raw.get("versions")
    if not isinstance(versions, dict):
        raw["versions"] = {}
    raw.setdefault("schema", _CACHE_VERSION)
    return raw


def _write_cache_file(data: dict[str, Any]) -> None:
    path = test_results_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    tmp.write_text(payload + "\n", encoding="utf-8")
    tmp.replace(path)
    debug("strategy_testing", f"test results cache saved ({path})")


def _row_to_dict(row: TargetProbeResult) -> dict[str, Any]:
    return {
        "name": row.name,
        "http_tokens": list(row.http_tokens),
        "ping": row.ping,
    }


def row_from_dict(data: dict[str, Any]) -> TargetProbeResult:
    tokens = data.get("http_tokens") or []
    if not isinstance(tokens, list):
        tokens = []
    return TargetProbeResult(
        name=str(data.get("name", "")),
        http_tokens=tuple(str(t) for t in tokens),
        ping=str(data.get("ping", "?")),
    )


def load_all_versions() -> dict[str, dict[str, dict[str, Any]]]:
    """Return ``{version: {strategy_id: entry}}`` from disk."""
    data = _read_cache_file()
    versions = data.get("versions")
    if not isinstance(versions, dict):
        return {}
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for version, bucket in versions.items():
        if not isinstance(version, str) or not isinstance(bucket, dict):
            continue
        out[version] = {str(sid): entry for sid, entry in bucket.items() if isinstance(entry, dict)}
    return out


def save_strategy_result(
    version: str,
    strategy_id: str,
    *,
    state: str,
    summary: str,
    detail: str = "",
    score: tuple[int, int] | None,
    rows: list[TargetProbeResult],
) -> None:
    """Merge one strategy result into the cache for ``version``."""
    if not version:
        return
    data = _read_cache_file()
    versions = data.setdefault("versions", {})
    if not isinstance(versions, dict):
        versions = {}
        data["versions"] = versions
    bucket = versions.setdefault(version, {})
    if not isinstance(bucket, dict):
        bucket = {}
        versions[version] = bucket
    bucket[strategy_id] = {
        "state": state,
        "summary": summary,
        "detail": detail,
        "score": list(score) if score else None,
        "rows": [_row_to_dict(row) for row in rows],
        "tested_at": _utc_now(),
    }
    _write_cache_file(data)


def remove_version(version: str) -> None:
    """Drop cached results when a flowseal version folder is deleted."""
    if not version:
        return
    data = _read_cache_file()
    versions = data.get("versions")
    if not isinstance(versions, dict) or version not in versions:
        return
    del versions[version]
    _write_cache_file(data)


def cache_path() -> Path:
    return test_results_cache_path()
