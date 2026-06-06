"""Information inbox — MPLAT-SPR-04."""

from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import jsonschema

from ..health_probe import probe_app
from ..registry import AppRegistration, AppRegistry, load_registry

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "miche_information_item.json"
_AUDIT_LOG = Path.home() / ".miche" / "miche_audit.jsonl"
_FETCH_LOG = Path.home() / ".miche" / "miche_information_fetch.jsonl"
_DEFAULT_TTL_SECONDS = 30.0
_BLOCK_ID_NA = "N/A"


@dataclass
class ProviderResult:
    provider: str
    ok: bool
    items: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass
class InformationInboxSnapshot:
    ok: bool
    items: list[dict[str, Any]]
    providers: list[dict[str, Any]]
    fetched_at: str
    cache_hit: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "items": self.items,
            "providers": self.providers,
            "fetched_at": self.fetched_at,
            "cache_hit": self.cache_hit,
        }


def _load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


def validate_information_item(item: dict[str, Any], *, schema: dict[str, Any] | None = None) -> None:
    jsonschema.validate(instance=item, schema=schema or _load_schema())


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_fetch_log(*, info_id: str, provider: str, kind: str) -> None:
    _FETCH_LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "info_id": info_id,
        "provider": provider,
        "kind": kind,
        "logged_at": _iso_now(),
    }
    with _FETCH_LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")


def _sort_key(item: dict[str, Any]) -> tuple[float, str]:
    score = -float(item.get("relevance_score") or 0)
    created = str(item.get("created_at") or "")
    return (score, created)


class InformationProvider(ABC):
    name: str

    @abstractmethod
    def collect(self, *, registry: AppRegistry) -> ProviderResult:
        """Return information cards for this provider."""


class GapProvider(InformationProvider):
    name = "gap"

    def __init__(self, *, fetch_gap_items: Callable[[AppRegistry], list[dict[str, Any]]] | None = None) -> None:
        self._fetch_gap_items = fetch_gap_items

    def collect(self, *, registry: AppRegistry) -> ProviderResult:
        if self._fetch_gap_items is None:
            return ProviderResult(provider=self.name, ok=True, items=[])
        try:
            items = self._fetch_gap_items(registry)
            return ProviderResult(provider=self.name, ok=True, items=items)
        except Exception as exc:
            return ProviderResult(provider=self.name, ok=False, error=str(exc))


class DeployProvider(InformationProvider):
    name = "deploy"

    def collect(self, *, registry: AppRegistry) -> ProviderResult:
        items: list[dict[str, Any]] = []
        try:
            for app in registry.enabled_apps():
                if not app.resolve_base_url():
                    continue
                result = probe_app(app, use_cache=True)
                if result.reason == "env_unset":
                    continue
                info_id = str(uuid.uuid4())
                if result.ok:
                    items.append(
                        {
                            "info_id": info_id,
                            "kind": "deploy_health",
                            "title": f"{app.display_name} deploy probe OK",
                            "body": f"Health check passed in {result.latency_ms}ms at {result.checked_at}.",
                            "block_id": _BLOCK_ID_NA,
                            "source_app": app.id,
                            "provider": self.name,
                            "relevance_score": 0.55,
                            "stale": False,
                            "degraded": False,
                            "created_at": result.checked_at,
                        }
                    )
                else:
                    items.append(
                        {
                            "info_id": info_id,
                            "kind": "deploy_health",
                            "title": f"{app.display_name} deploy probe failed",
                            "body": f"Reason: {result.reason or 'unreachable'}. Probe failed — deploy status unknown.",
                            "block_id": _BLOCK_ID_NA,
                            "source_app": app.id,
                            "provider": self.name,
                            "relevance_score": 0.7,
                            "stale": True,
                            "degraded": True,
                            "created_at": result.checked_at,
                        }
                    )
            return ProviderResult(provider=self.name, ok=True, items=items)
        except Exception as exc:
            return ProviderResult(provider=self.name, ok=False, error=str(exc))


class AuditProvider(InformationProvider):
    name = "audit"

    def collect(self, *, registry: AppRegistry) -> ProviderResult:
        try:
            if not _AUDIT_LOG.is_file():
                return ProviderResult(provider=self.name, ok=True, items=[])
            last_line = ""
            with _AUDIT_LOG.open() as f:
                for line in f:
                    if line.strip():
                        last_line = line.strip()
            if not last_line:
                return ProviderResult(provider=self.name, ok=True, items=[])
            row = json.loads(last_line)
            info_id = str(uuid.uuid4())
            return ProviderResult(
                provider=self.name,
                ok=True,
                items=[
                    {
                        "info_id": info_id,
                        "kind": "audit_snippet",
                        "title": row.get("title") or "Last Miche audit",
                        "body": row.get("body") or row.get("snippet") or last_line[:500],
                        "block_id": row.get("block_id") or _BLOCK_ID_NA,
                        "source_app": row.get("source_app") or "miche_platform",
                        "provider": self.name,
                        "relevance_score": float(row.get("relevance_score") or 0.6),
                        "stale": bool(row.get("stale", False)),
                        "degraded": False,
                        "created_at": row.get("created_at") or _iso_now(),
                    }
                ],
            )
        except Exception as exc:
            return ProviderResult(provider=self.name, ok=False, error=str(exc))


def _degraded_card(*, provider: str, error: str, source_app: str = "miche_platform") -> dict[str, Any]:
    return {
        "info_id": str(uuid.uuid4()),
        "kind": "audit_snippet",
        "title": f"{provider} provider degraded",
        "body": error,
        "block_id": _BLOCK_ID_NA,
        "source_app": source_app,
        "provider": provider,
        "relevance_score": 0.4,
        "stale": True,
        "degraded": True,
        "created_at": _iso_now(),
    }


class InformationInboxAggregator:
    def __init__(
        self,
        *,
        registry: AppRegistry | None = None,
        providers: list[InformationProvider] | None = None,
        ttl_seconds: float = _DEFAULT_TTL_SECONDS,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._registry = registry
        self._providers = providers or [GapProvider(), DeployProvider(), AuditProvider()]
        self._ttl = ttl_seconds
        self._now = now or time.time
        self._cache: InformationInboxSnapshot | None = None
        self._cache_at: float = 0.0

    def _registry_loaded(self) -> AppRegistry:
        return self._registry or load_registry()

    def collect(self, *, force: bool = False) -> InformationInboxSnapshot:
        now_ts = self._now()
        if (
            not force
            and self._cache is not None
            and (now_ts - self._cache_at) < self._ttl
        ):
            return InformationInboxSnapshot(
                ok=self._cache.ok,
                items=list(self._cache.items),
                providers=list(self._cache.providers),
                fetched_at=self._cache.fetched_at,
                cache_hit=True,
            )

        reg = self._registry_loaded()
        merged: list[dict[str, Any]] = []
        provider_status: list[dict[str, Any]] = []

        for provider in self._providers:
            try:
                result = provider.collect(registry=reg)
            except Exception as exc:
                result = ProviderResult(provider=provider.name, ok=False, error=str(exc))
            provider_status.append(
                {
                    "provider": result.provider,
                    "ok": result.ok,
                    "error": result.error,
                    "count": len(result.items),
                }
            )
            if result.ok:
                for raw in result.items:
                    item = dict(raw)
                    item.setdefault("info_id", str(uuid.uuid4()))
                    item.setdefault("block_id", _BLOCK_ID_NA)
                    validate_information_item(item)
                    _append_fetch_log(
                        info_id=item["info_id"],
                        provider=item["provider"],
                        kind=item["kind"],
                    )
                    merged.append(item)
            elif result.error:
                card = _degraded_card(provider=result.provider, error=result.error)
                validate_information_item(card)
                _append_fetch_log(
                    info_id=card["info_id"],
                    provider=card["provider"],
                    kind=card["kind"],
                )
                merged.append(card)

        items = sorted(merged, key=_sort_key)
        fetched_at = _iso_now()
        snapshot = InformationInboxSnapshot(
            ok=True,
            items=items,
            providers=provider_status,
            fetched_at=fetched_at,
        )
        self._cache = snapshot
        self._cache_at = now_ts
        return snapshot