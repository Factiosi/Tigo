"""In-memory per-strategy test results with persistent cache per flowseal version."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

from src.core.settings import get_settings
from src.modules.strategy_testing import cache as results_cache
from src.modules.strategy_testing.probe import TargetProbeResult, load_targets

StrategyResultState = Literal["untested", "running", "full", "partial", "failed", "unknown"]
CellPhase = Literal["pending", "loading", "done"]
ResultEvent = Literal["probe", "status", "list"]


@dataclass(frozen=True)
class ResultChange:
    strategy_id: str | None = None
    event: ResultEvent = "list"

_STATUS_SUMMARY = {
    "untested": "Не протестирована",
    "running": "Не протестирована",
    "full": "Полностью работает (лучший выбор)",
    "partial": "Частично работает",
    "failed": "Не работает",
    "unknown": "Не работает",
}


@dataclass
class ProbeCell:
    phase: CellPhase = "pending"
    text: str = "?"


@dataclass
class ProbeTableRow:
    name: str
    http: ProbeCell | None
    tls12: ProbeCell | None
    tls13: ProbeCell | None
    ping: ProbeCell


@dataclass
class StrategyTestResult:
    strategy_id: str
    state: StrategyResultState = "untested"
    summary: str = "?"
    detail: str = ""
    rows: list[TargetProbeResult] = field(default_factory=list)
    score: tuple[int, int] | None = None


_listeners: list[Callable[[ResultChange], None]] = []
_results: dict[str, StrategyTestResult] = {}
_probe_tables: dict[str, list[ProbeTableRow]] = {}
_current: tuple[str, str] | None = None
_cache_loaded = False


def _key(version: str, strategy_id: str) -> str:
    return f"{version}\x1f{strategy_id}"


def _resolve_version(version: str | None) -> str:
    if version:
        return version
    return get_settings().active_version or ""


def subscribe(listener: Callable[[ResultChange], None]) -> None:
    _listeners.append(listener)


def unsubscribe(listener: Callable[[ResultChange], None]) -> None:
    if listener in _listeners:
        _listeners.remove(listener)


def _notify(*, strategy_id: str | None = None, event: ResultEvent = "list") -> None:
    change = ResultChange(strategy_id=strategy_id, event=event)
    for listener in list(_listeners):
        listener(change)


def _pending_cell() -> ProbeCell:
    return ProbeCell("pending", "?")


def default_probe_table() -> list[ProbeTableRow]:
    rows: list[ProbeTableRow] = []
    for target in load_targets():
        if target.url:
            rows.append(
                ProbeTableRow(
                    name=target.name,
                    http=_pending_cell(),
                    tls12=_pending_cell(),
                    tls13=_pending_cell(),
                    ping=ProbeCell("pending", "? ms"),
                )
            )
        else:
            rows.append(
                ProbeTableRow(
                    name=target.name,
                    http=None,
                    tls12=None,
                    tls13=None,
                    ping=ProbeCell("pending", "? ms"),
                )
            )
    return rows


def _token_map(http_tokens: tuple[str, ...]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for token in http_tokens:
        if ":" in token:
            label, value = token.split(":", 1)
            mapping[label] = value
    return mapping


def _result_to_table_row(result: TargetProbeResult) -> ProbeTableRow:
    if result.http_tokens:
        tokens = _token_map(result.http_tokens)
        return ProbeTableRow(
            name=result.name,
            http=ProbeCell("done", f"HTTP:{tokens.get('HTTP', 'ERROR')}"),
            tls12=ProbeCell("done", f"TLS1.2:{tokens.get('TLS1.2', 'ERROR')}"),
            tls13=ProbeCell("done", f"TLS1.3:{tokens.get('TLS1.3', 'ERROR')}"),
            ping=ProbeCell("done", result.ping),
        )
    return ProbeTableRow(
        name=result.name,
        http=None,
        tls12=None,
        tls13=None,
        ping=ProbeCell("done", result.ping),
    )


def _hydrate_entry(version: str, strategy_id: str, entry: dict) -> None:
    state = entry.get("state", "untested")
    if state not in _STATUS_SUMMARY:
        return
    rows_raw = entry.get("rows") or []
    rows: list[TargetProbeResult] = []
    if isinstance(rows_raw, list):
        for item in rows_raw:
            if isinstance(item, dict):
                rows.append(results_cache.row_from_dict(item))
    score_raw = entry.get("score")
    score: tuple[int, int] | None = None
    if isinstance(score_raw, list) and len(score_raw) == 2:
        try:
            score = (int(score_raw[0]), int(score_raw[1]))
        except (TypeError, ValueError):
            score = None
    item = StrategyTestResult(
        strategy_id=strategy_id,
        state=state,  # type: ignore[arg-type]
        summary=str(entry.get("summary") or _STATUS_SUMMARY.get(state, "?")),
        detail=str(entry.get("detail") or ""),
        rows=rows,
        score=score,
    )
    cache_key = _key(version, strategy_id)
    _results[cache_key] = item
    if rows:
        _probe_tables[cache_key] = [_result_to_table_row(row) for row in rows]


def load_cache() -> None:
    """Load persisted test results for all installed flowseal versions."""
    global _cache_loaded
    if _cache_loaded:
        return
    for version, bucket in results_cache.load_all_versions().items():
        for strategy_id, entry in bucket.items():
            _hydrate_entry(version, strategy_id, entry)
    _cache_loaded = True


def get_probe_table(strategy_id: str, *, version: str | None = None) -> list[ProbeTableRow]:
    ver = _resolve_version(version)
    cache_key = _key(ver, strategy_id)
    if cache_key in _probe_tables:
        return _probe_tables[cache_key]
    item = _results.get(cache_key)
    if item and item.rows:
        return [_result_to_table_row(row) for row in item.rows]
    return []


def init_probe_table(strategy_id: str, *, version: str | None = None) -> None:
    ver = _resolve_version(version)
    _probe_tables[_key(ver, strategy_id)] = default_probe_table()


def set_probe_loading(strategy_id: str, *, version: str | None = None) -> None:
    ver = _resolve_version(version)
    cache_key = _key(ver, strategy_id)
    table = _probe_tables.get(cache_key)
    if not table:
        init_probe_table(strategy_id, version=ver)
        table = _probe_tables[cache_key]
    for row in table:
        if row.http:
            row.http.phase = "loading"
        if row.tls12:
            row.tls12.phase = "loading"
        if row.tls13:
            row.tls13.phase = "loading"
        row.ping.phase = "loading"
    _notify(strategy_id=strategy_id, event="probe")


def apply_probe_result(
    strategy_id: str,
    result: TargetProbeResult,
    *,
    version: str | None = None,
) -> None:
    ver = _resolve_version(version)
    table = _probe_tables.get(_key(ver, strategy_id))
    if not table:
        return
    for row in table:
        if row.name != result.name:
            continue
        if result.http_tokens:
            tokens = _token_map(result.http_tokens)
            if row.http:
                row.http = ProbeCell("done", f"HTTP:{tokens.get('HTTP', 'ERROR')}")
            if row.tls12:
                row.tls12 = ProbeCell("done", f"TLS1.2:{tokens.get('TLS1.2', 'ERROR')}")
            if row.tls13:
                row.tls13 = ProbeCell("done", f"TLS1.3:{tokens.get('TLS1.3', 'ERROR')}")
        row.ping = ProbeCell("done", result.ping)
        break
    _notify(strategy_id=strategy_id, event="probe")


def get_result(strategy_id: str, *, version: str | None = None) -> StrategyTestResult | None:
    ver = _resolve_version(version)
    item = _results.get(_key(ver, strategy_id))
    if item is None or item.state == "untested":
        return None
    return item


def get_or_create(strategy_id: str, *, version: str | None = None) -> StrategyTestResult:
    ver = _resolve_version(version)
    cache_key = _key(ver, strategy_id)
    if cache_key not in _results:
        _results[cache_key] = StrategyTestResult(strategy_id=strategy_id)
    return _results[cache_key]


def current_strategy_id() -> str | None:
    if _current is None:
        return None
    return _current[1]


def begin_test_run(*, version: str | None = None) -> None:
    """Start a test run without clearing prior results (re-tests keep status and sort order)."""
    global _current
    _current = None


def clear_session(
    *,
    version: str | None = None,
    strategy_ids: list[str] | None = None,
) -> None:
    global _current
    ver = _resolve_version(version)
    _current = None
    if strategy_ids is None:
        keys = [key for key in _results if key.startswith(f"{ver}\x1f")]
        for key in keys:
            _results.pop(key, None)
            _probe_tables.pop(key, None)
    else:
        for sid in strategy_ids:
            cache_key = _key(ver, sid)
            _results[cache_key] = StrategyTestResult(strategy_id=sid)
            _probe_tables.pop(cache_key, None)
    _notify(event="list")


def set_running(strategy_id: str, *, version: str | None = None) -> None:
    global _current
    ver = _resolve_version(version)
    _current = (ver, strategy_id)
    init_probe_table(strategy_id, version=ver)
    _notify(strategy_id=strategy_id, event="status")


def set_result(
    strategy_id: str,
    *,
    version: str | None = None,
    state: StrategyResultState,
    rows: list[TargetProbeResult],
    score: tuple[int, int] | None,
    detail: str = "",
) -> None:
    global _current
    ver = _resolve_version(version)
    if _current == (ver, strategy_id):
        _current = None
    item = get_or_create(strategy_id, version=ver)
    item.state = state
    item.summary = _STATUS_SUMMARY.get(state, "?")
    item.detail = detail.strip()
    item.rows = list(rows)
    item.score = score
    cache_key = _key(ver, strategy_id)
    if rows:
        _probe_tables[cache_key] = [_result_to_table_row(row) for row in rows]
    elif cache_key not in _probe_tables:
        _probe_tables[cache_key] = default_probe_table()
    if state not in {"untested", "running"}:
        results_cache.save_strategy_result(
            ver,
            strategy_id,
            state=state,
            summary=item.summary,
            detail=item.detail,
            score=score,
            rows=rows,
        )
    _notify(strategy_id=strategy_id, event="status")


def is_tested(strategy_id: str, *, version: str | None = None) -> bool:
    ver = _resolve_version(version)
    item = _results.get(_key(ver, strategy_id))
    return item is not None and item.state not in {"untested", "running"}


def summary_for(strategy_id: str, *, version: str | None = None) -> str:
    ver = _resolve_version(version)
    item = _results.get(_key(ver, strategy_id))
    if not item or item.state == "untested":
        return "Не протестирована"
    return item.summary


def drop_version(version: str) -> None:
    """Remove cached results for a deleted flowseal version."""
    if not version:
        return
    prefix = f"{version}\x1f"
    for key in list(_results):
        if key.startswith(prefix):
            _results.pop(key, None)
            _probe_tables.pop(key, None)
    results_cache.remove_version(version)
    _notify(event="list")
