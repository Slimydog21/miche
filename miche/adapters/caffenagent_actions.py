"""caffenagent action inbox adapter — MPLAT-SPR-03."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from ..inbox.action import AppFetchResult
from ..registry import AppRegistration

_ACTIONS_PATH = "/api/inbox/actions"
_SESSIONS_PATH = "/api/sessions/registry"
_TIMEOUT = 5.0


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _map_remote_action(raw: dict[str, Any], *, source_app: str) -> dict[str, Any]:
    return {
        "action_id": raw.get("action_id") or str(uuid.uuid4()),
        "title": str(raw.get("title") or "Action required"),
        "detail": raw.get("detail"),
        "severity": raw.get("severity") or "soon",
        "source_app": raw.get("source_app") or source_app,
        "stale": bool(raw.get("stale", False)),
        "focus_deep_link": raw.get("focus_deep_link"),
        "created_at": raw.get("created_at") or _iso_now(),
    }


def _from_sessions_registry(body: dict[str, Any], *, source_app: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in body.get("sessions") or body.get("items") or []:
        status = str(row.get("status") or "").lower()
        if status not in {"stale", "blocked", "stuck"}:
            continue
        sid = row.get("session_id") or row.get("id") or "session"
        items.append(
            {
                "action_id": str(uuid.uuid4()),
                "title": f"Session {sid} {status}",
                "detail": row.get("summary") or row.get("label"),
                "severity": "blocking" if status == "blocked" else "soon",
                "source_app": source_app,
                "stale": False,
                "focus_deep_link": "/orchestrate",
                "created_at": row.get("updated_at") or _iso_now(),
            }
        )
    return items


def fetch_caffenagent_actions(
    app: AppRegistration,
    *,
    client: httpx.Client | None = None,
) -> AppFetchResult:
    base = app.resolve_base_url()
    if not base:
        return AppFetchResult(
            app_id=app.id,
            ok=False,
            error="env_unset",
            stale=True,
        )

    owns_client = client is None
    http = client or httpx.Client(timeout=_TIMEOUT)
    try:
        actions_url = f"{base.rstrip('/')}{_ACTIONS_PATH}"
        r = http.get(actions_url)
        if r.status_code == 200:
            body = r.json()
            raw_items = body.get("items") or body.get("actions") or []
            mapped = [_map_remote_action(x, source_app=app.id) for x in raw_items]
            return AppFetchResult(app_id=app.id, ok=True, items=mapped, stale=False)

        if r.status_code == 404:
            sessions_url = f"{base.rstrip('/')}{_SESSIONS_PATH}"
            sr = http.get(sessions_url)
            if sr.status_code == 200:
                mapped = _from_sessions_registry(sr.json(), source_app=app.id)
                return AppFetchResult(app_id=app.id, ok=True, items=mapped, stale=False)
            return AppFetchResult(
                app_id=app.id,
                ok=False,
                error=f"sessions registry HTTP {sr.status_code}",
                stale=True,
            )

        return AppFetchResult(
            app_id=app.id,
            ok=False,
            error=f"inbox actions HTTP {r.status_code}",
            stale=True,
        )
    except httpx.HTTPError as exc:
        return AppFetchResult(app_id=app.id, ok=False, error=str(exc), stale=True)
    finally:
        if owns_client:
            http.close()


def make_fetcher(client: httpx.Client | None = None):
    def _fetch(app: AppRegistration) -> AppFetchResult:
        if app.id != "caffenagent":
            return AppFetchResult(app_id=app.id, ok=True, items=[])
        return fetch_caffenagent_actions(app, client=client)

    return _fetch