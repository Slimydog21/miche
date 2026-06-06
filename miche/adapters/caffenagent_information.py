"""caffenagent information adapter — read-only MPLAT-SPR-04."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from ..registry import AppRegistry

_INFO_PATH = "/api/inbox/information"
_GAP_PATH_TEMPLATE = "/api/gap/{parent_run_id}"
_TIMEOUT = 5.0
_BLOCK_ID_NA = "N/A"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _block_id_from_gap(gap: dict[str, Any]) -> str:
    for source in gap.get("sources") or []:
        if source.get("kind") == "voice_block":
            ref = str(source.get("ref") or "")
            if ref:
                return ref
    return _BLOCK_ID_NA


def _gap_to_info_item(gap: dict[str, Any], *, parent_run_id: str) -> dict[str, Any]:
    severity = str(gap.get("severity") or "major")
    relevance = {"blocker": 0.95, "major": 0.85, "minor": 0.65}.get(severity, 0.7)
    claim = str(gap.get("claim") or "Gap detected")
    counter = str(gap.get("counterclaim") or "")
    body = claim
    if counter:
        body = f"{claim}\n\nCounterclaim: {counter}"
    return {
        "info_id": str(uuid.uuid4()),
        "kind": "gap_summary",
        "title": f"Gap {gap.get('id', 'unknown')} — {severity}",
        "body": body,
        "block_id": _block_id_from_gap(gap),
        "source_app": "caffenagent",
        "provider": "gap",
        "relevance_score": relevance,
        "stale": False,
        "degraded": False,
        "created_at": _iso_now(),
    }


def fetch_caffenagent_information(
    *,
    base_url: str,
    parent_run_id: str | None = None,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Read-only GET adapter — never POST/PUT/PATCH."""
    owns_client = client is None
    http = client or httpx.Client(timeout=_TIMEOUT)
    try:
        info_url = f"{base_url.rstrip('/')}{_INFO_PATH}"
        r = http.get(info_url)
        if r.status_code == 200:
            body = r.json()
            raw_items = body.get("items") or body.get("information") or []
            return [dict(x) for x in raw_items]

        run_id = parent_run_id or os.environ.get("CAFFENAGENT_GAP_PARENT_RUN_ID", "").strip()
        if not run_id:
            return []

        gap_url = f"{base_url.rstrip('/')}{_GAP_PATH_TEMPLATE.format(parent_run_id=run_id)}"
        gr = http.get(gap_url)
        if gr.status_code != 200:
            return []
        report = gr.json()
        gaps = report.get("gaps") or []
        open_gaps = [g for g in gaps if g.get("status", "open") in ("open", "disputed", "narrowed")]
        return [_gap_to_info_item(g, parent_run_id=run_id) for g in open_gaps[:10]]
    finally:
        if owns_client:
            http.close()


def make_gap_fetcher(client: httpx.Client | None = None):
    def _fetch(registry: AppRegistry) -> list[dict[str, Any]]:
        app = registry.get("caffenagent")
        if app is None or not app.enabled:
            return []
        base = app.resolve_base_url()
        if not base:
            return []
        return fetch_caffenagent_information(base_url=base, client=client)

    return _fetch