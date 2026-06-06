"""Island utterance router — delegates to intent router MPLAT-SPR-06."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..router.dispatch import dispatch_for_island, dispatch_mode
from ..tenancy.profiles import active_profile_id

# Tests monkeypatch this; production prefers MICHE_ISLAND_UTTERANCE_LOG env.
_UTTERANCE_LOG: Path = Path("logs/miche_island_utterance.jsonl")


def _default_utterance_log() -> Path:
    override = os.environ.get("MICHE_ISLAND_UTTERANCE_LOG", "").strip()
    if override:
        return Path(override)
    return _UTTERANCE_LOG





def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utterance_log_path() -> Path:
    return _default_utterance_log()


def router_mode() -> str:
    return dispatch_mode()


def _append_utterance_audit(row: dict[str, Any], *, path: Path | None = None) -> None:
    log = path or _default_utterance_log()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as f:
        f.write(json.dumps(row) + "\n")


def route_utterance(
    *,
    utterance_id: str,
    text: str | None = None,
    audio_blob_id: str | None = None,
    source: str = "island",
    audit_path: Path | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    body_text = (text or "").strip()
    result = dispatch_for_island(
        utterance_id=utterance_id,
        text=body_text or "(voice)",
        audio_blob_id=audio_blob_id,
        source=source,
    )

    latency_ms = int((time.monotonic() - started) * 1000)
    result["latency_ms"] = max(result.get("latency_ms", 0), latency_ms)
    if latency_ms > 5000:
        result["timeout_badge"] = True

    audit = {
        "utterance_id": utterance_id,
        "text": body_text or None,
        "audio_blob_id": audio_blob_id,
        "source": source,
        "profile_id": active_profile_id(),
        "needs_focus": result.get("needs_focus", False),
        "router_mode": result.get("router_mode", router_mode()),
        "router_decision_id": result.get("router_decision_id"),
        "latency_ms": latency_ms,
        "created_at": _iso_now(),
    }
    _append_utterance_audit(audit, path=audit_path)
    return result


def new_utterance_id() -> str:
    return str(uuid.uuid4())