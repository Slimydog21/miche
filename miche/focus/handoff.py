"""Focus handoff tokens — MPLAT-SPR-07."""

from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import jsonschema

from ..registry import AppRegistration, RegistryError, load_registry

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "miche_focus_handoff.json"
_HANDOFF_STORE = Path.home() / ".miche" / "focus_handoffs.jsonl"
_TTL_HOURS = 24


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def handoff_store_path() -> Path:
    override = os.environ.get("MICHE_FOCUS_HANDOFF_STORE", "").strip()
    if override:
        return Path(override)
    return _HANDOFF_STORE


def _load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


def validate_handoff(row: dict[str, Any]) -> None:
    jsonschema.validate(instance=row, schema=_load_schema())


def _append_row(row: dict[str, Any], *, path: Path | None = None) -> None:
    store = path or handoff_store_path()
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a") as f:
        f.write(json.dumps(row) + "\n")


def _read_rows(*, path: Path | None = None) -> list[dict[str, Any]]:
    store = path or handoff_store_path()
    if not store.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with store.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _parse_expires(expires_at: str) -> datetime:
    return datetime.fromisoformat(expires_at.replace("Z", "+00:00"))


def allowed_focus_paths(app: AppRegistration) -> set[str]:
    paths: set[str] = set()
    if app.focus_route:
        paths.add(app.focus_route)
    extra = getattr(app, "focus_paths", None) or []
    for p in extra:
        if str(p).startswith("/"):
            paths.add(str(p))
    for cap in app.capabilities:
        invoke = cap.invoke.split(" ", 1)
        if len(invoke) == 2 and invoke[1].startswith("/"):
            paths.add(invoke[1])
    return paths


def _normalize_path(path: str) -> str:
    import posixpath

    cleaned = posixpath.normpath(path.strip())
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    if cleaned.startswith("//"):
        raise ValueError("open redirect rejected")
    return cleaned


def validate_focus_path(app: AppRegistration, path: str) -> str:
    normalized = _normalize_path(path)
    if ".." in path.split("/"):
        raise ValueError("path traversal rejected")
    allowed = allowed_focus_paths(app)
    if allowed and normalized not in allowed:
        if not any(normalized == p or normalized.startswith(p.rstrip("/") + "/") for p in allowed):
            raise ValueError(f"path not allowed; allowed: {sorted(allowed)}")
    return normalized


def _host_allowed(target_url: str, base_url: str) -> bool:
    target_host = urlparse(target_url).hostname
    base_host = urlparse(base_url).hostname
    if not target_host or not base_host:
        return False
    return target_host == base_host


def build_target_url(app: AppRegistration, path: str) -> str | None:
    base = app.resolve_base_url()
    if not base:
        return None
    base = base.rstrip("/")
    url = f"{base}{path}"
    if not _host_allowed(url, base):
        raise ValueError("target host must match registry base_url")
    return url


def create_handoff(
    *,
    app_id: str,
    path: str,
    island_expanded: bool = False,
    utterance_id: str | None = None,
    router_decision_id: str | None = None,
    return_url: str = "/",
    store_path: Path | None = None,
) -> dict[str, Any]:
    if not return_url.startswith("/") or return_url.startswith("//"):
        raise ValueError("return_url must be same-origin path")

    reg = load_registry()
    app = reg.get(app_id)
    if not app or not app.enabled:
        raise RegistryError(f"unknown or disabled app: {app_id}")

    focus_path = validate_focus_path(app, path)
    target_url = build_target_url(app, focus_path)
    embed_allowed = bool(getattr(app, "focus_embed_allowed", False))
    if target_url and embed_allowed:
        embed_mode = "iframe"
    elif target_url:
        embed_mode = "navigate"
    else:
        embed_mode = "degraded"

    handoff_id = str(uuid.uuid4())
    island_state_token = secrets.token_urlsafe(16)
    expires = datetime.now(timezone.utc) + timedelta(hours=_TTL_HOURS)

    row = {
        "handoff_id": handoff_id,
        "app_id": app_id,
        "path": focus_path,
        "return_url": return_url,
        "island_state_token": island_state_token,
        "island_expanded": island_expanded,
        "utterance_id": utterance_id,
        "router_decision_id": router_decision_id,
        "target_url": target_url,
        "embed_mode": embed_mode,
        "expires_at": expires.isoformat(),
        "created_at": _iso_now(),
    }
    validate_handoff(row)
    _append_row(row, path=store_path)
    return row


def load_handoff(handoff_id: str, *, store_path: Path | None = None) -> dict[str, Any] | None:
    for row in reversed(_read_rows(path=store_path)):
        if row.get("handoff_id") == handoff_id:
            expires = _parse_expires(str(row["expires_at"]))
            if expires < datetime.now(timezone.utc):
                return None
            return row
    return None


def restore_payload(handoff_id: str, *, store_path: Path | None = None) -> dict[str, Any] | None:
    row = load_handoff(handoff_id, store_path=store_path)
    if not row:
        return None
    return {
        "ok": True,
        "handoff_id": row["handoff_id"],
        "island_state_token": row["island_state_token"],
        "island_expanded": bool(row.get("island_expanded")),
        "return_url": row["return_url"],
    }