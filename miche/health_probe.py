"""Health probe service — MPLAT-SPR-01."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .registry import AppRegistration, AppRegistry, load_registry

_PROBE_LOG = Path.home() / ".miche" / "miche_health_probe.jsonl"
_CACHE_TTL_S = 30


@dataclass
class ProbeResult:
    app_id: str
    ok: bool
    latency_ms: float | None
    checked_at: str
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class _ProbeCache:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, ProbeResult]] = {}

    def get(self, app_id: str) -> ProbeResult | None:
        row = self._entries.get(app_id)
        if row is None:
            return None
        ts, result = row
        if result.ok and (time.monotonic() - ts) > _CACHE_TTL_S:
            return None
        if result.ok:
            return result
        return None

    def set(self, app_id: str, result: ProbeResult) -> None:
        self._entries[app_id] = (time.monotonic(), result)


_cache = _ProbeCache()


def _append_jsonl(row: dict[str, Any]) -> None:
    _PROBE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _PROBE_LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")


def probe_app(
    app: AppRegistration,
    *,
    client: httpx.Client | None = None,
    use_cache: bool = True,
) -> ProbeResult:
    """Probe one app health endpoint."""
    if use_cache and not owns_client_precheck(app):
        cached = _cache.get(app.id)
        if cached is not None:
            return cached

    now = datetime.now(timezone.utc).isoformat()
    base = app.resolve_base_url()
    if not base:
        result = ProbeResult(
            app_id=app.id,
            ok=False,
            latency_ms=None,
            checked_at=now,
            reason="env_unset",
        )
        _cache.set(app.id, result)
        return result

    url = base.rstrip("/") + app.health_path
    owns_client = client is None
    http = client or httpx.Client(timeout=5.0)
    try:
        start = time.perf_counter()
        resp = http.get(url)
        latency = (time.perf_counter() - start) * 1000.0
        ok = 200 <= resp.status_code < 300
        result = ProbeResult(
            app_id=app.id,
            ok=ok,
            latency_ms=round(latency, 2),
            checked_at=now,
            reason=None if ok else f"http_{resp.status_code}",
        )
    except httpx.HTTPError as exc:
        result = ProbeResult(
            app_id=app.id,
            ok=False,
            latency_ms=None,
            checked_at=now,
            reason=f"http_error:{type(exc).__name__}",
        )
    finally:
        if owns_client:
            http.close()

    if result.ok:
        _cache.set(app.id, result)
    return result


def probe_registry(
    registry: AppRegistry | None = None,
    *,
    client: httpx.Client | None = None,
    app_id: str | None = None,
) -> list[ProbeResult]:
    """Probe all enabled apps (or one by id)."""
    reg = registry or load_registry()
    targets = reg.enabled_apps()
    if app_id:
        app = reg.get(app_id)
        if app is None:
            raise KeyError(f"unknown app_id: {app_id}")
        targets = [app]

    results: list[ProbeResult] = []
    owns_client = client is None
    http = client or httpx.Client(timeout=5.0)
    try:
        for app in targets:
            results.append(probe_app(app, client=http, use_cache=False))
    finally:
        if owns_client:
            http.close()

    _append_jsonl(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "batch_size": len(results),
            "results": [r.as_dict() for r in results],
        }
    )
    return results