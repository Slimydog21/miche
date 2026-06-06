"""Action inbox aggregator — MPLAT-SPR-03."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import jsonschema

from ..registry import AppRegistration, AppRegistry, load_registry

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "miche_action_item.json"
_SEVERITY_ORDER = {"blocking": 0, "soon": 1, "nit": 2}
_DEFAULT_TTL_SECONDS = 30.0


@dataclass
class AppFetchResult:
    app_id: str
    ok: bool
    items: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    stale: bool = False


@dataclass
class ActionInboxSnapshot:
    ok: bool
    items: list[dict[str, Any]]
    apps: list[dict[str, Any]]
    fetched_at: str
    cache_hit: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "items": self.items,
            "apps": self.apps,
            "fetched_at": self.fetched_at,
            "cache_hit": self.cache_hit,
        }


def _load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


def validate_action_item(item: dict[str, Any], *, schema: dict[str, Any] | None = None) -> None:
    jsonschema.validate(instance=item, schema=schema or _load_schema())


def _sort_key(item: dict[str, Any]) -> tuple[int, str]:
    sev = _SEVERITY_ORDER.get(str(item.get("severity")), 99)
    created = str(item.get("created_at") or "")
    return (sev, created)


def _stable_sort(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=_sort_key)


class ActionInboxAggregator:
    """Poll registered apps and merge action rows with TTL cache."""

    def __init__(
        self,
        *,
        registry: AppRegistry | None = None,
        ttl_seconds: float = _DEFAULT_TTL_SECONDS,
        fetcher: Callable[[AppRegistration], AppFetchResult] | None = None,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._registry = registry
        self._ttl = ttl_seconds
        self._fetcher = fetcher
        self._now = now or time.time
        self._cache: ActionInboxSnapshot | None = None
        self._cache_at: float = 0.0

    def _registry_loaded(self) -> AppRegistry:
        return self._registry or load_registry()

    def _fetch_app(self, app: AppRegistration) -> AppFetchResult:
        if self._fetcher is not None:
            return self._fetcher(app)
        return AppFetchResult(app_id=app.id, ok=True, items=[], stale=False)

    def collect(self, *, force: bool = False) -> ActionInboxSnapshot:
        now_ts = self._now()
        if (
            not force
            and self._cache is not None
            and (now_ts - self._cache_at) < self._ttl
        ):
            return ActionInboxSnapshot(
                ok=self._cache.ok,
                items=list(self._cache.items),
                apps=list(self._cache.apps),
                fetched_at=self._cache.fetched_at,
                cache_hit=True,
            )

        reg = self._registry_loaded()
        merged: list[dict[str, Any]] = []
        app_status: list[dict[str, Any]] = []

        for app in reg.enabled_apps():
            result = self._fetch_app(app)
            app_status.append(
                {
                    "app_id": result.app_id,
                    "ok": result.ok,
                    "stale": result.stale or not result.ok,
                    "error": result.error,
                    "count": len(result.items),
                }
            )
            if result.ok:
                for raw in result.items:
                    item = dict(raw)
                    item.setdefault("source_app", app.id)
                    if result.stale:
                        item["stale"] = True
                    if "action_id" not in item:
                        item["action_id"] = str(uuid.uuid4())
                    validate_action_item(item)
                    merged.append(item)
            elif result.error:
                merged.append(
                    {
                        "action_id": str(uuid.uuid4()),
                        "title": f"{app.display_name} unreachable",
                        "detail": result.error,
                        "severity": "soon",
                        "source_app": app.id,
                        "stale": True,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

        items = _stable_sort(merged)
        fetched_at = datetime.now(timezone.utc).isoformat()
        snapshot = ActionInboxSnapshot(ok=True, items=items, apps=app_status, fetched_at=fetched_at)
        self._cache = snapshot
        self._cache_at = now_ts
        return snapshot