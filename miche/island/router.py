"""Island utterance router — MPLAT-SPR-05 (cassette until SPR-06)."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _default_utterance_log() -> Path:
    override = os.environ.get("MICHE_ISLAND_UTTERANCE_LOG", "").strip()
    if override:
        return Path(override)
    return Path("logs/miche_island_utterance.jsonl")


_UTTERANCE_LOG = _default_utterance_log()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utterance_log_path() -> Path:
    return _UTTERANCE_LOG


def router_mode() -> str:
    if os.environ.get("MICHE_ISLAND_ROUTER_FIXTURE", "").strip().lower() == "cassette":
        return "cassette"
    if os.environ.get("MICHE_INTENT_ROUTER_URL", "").strip():
        return "production"
    return "cassette"


def _append_utterance_audit(row: dict[str, Any], *, path: Path | None = None) -> None:
    log = path or _UTTERANCE_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as f:
        f.write(json.dumps(row) + "\n")


def _action_inbox_cards() -> tuple[list[dict[str, Any]], str]:
    from ..routes.inbox import get_action_inbox

    inbox = get_action_inbox()
    items = inbox.get("items") or []
    cards: list[dict[str, Any]] = []
    for item in items[:3]:
        cards.append(
            {
                "type": "action_item",
                "title": str(item.get("title") or "Action item"),
                "body": str(item.get("summary") or item.get("body") or ""),
                "source_app_id": str(item.get("app_id") or "unknown"),
                "deep_link": item.get("deep_link"),
            }
        )
    if cards:
        return cards, f"Pulled {len(cards)} action item(s) from the inbox."
    cards.append(
        {
            "type": "info_summary",
            "title": "Action inbox empty",
            "body": "No must-do items right now — inbox is honestly empty.",
            "source_app_id": "miche",
        }
    )
    return cards, "Nothing blocked in the action inbox."


def _cassette_reply(*, text: str, utterance_id: str) -> dict[str, Any]:
    lowered = text.lower()
    cards: list[dict[str, Any]] = []
    needs_focus = False
    suggested_focus = None
    reply = "I'm here on the island — triage first, Focus only when you need depth."

    if "blocked" in lowered or "stale" in lowered:
        cards, reply = _action_inbox_cards()
    elif "gap" in lowered or "egghead" in lowered:
        cards.append(
            {
                "type": "route_progress",
                "title": "Router cassette: egghead dispatch",
                "body": "Would route to caffenagent.gap_review (SPR-06).",
                "source_app_id": "caffenagent",
                "run_id": "cassette-run-001",
            }
        )
        reply = "Dispatch queued in cassette mode — no fake 'I started egghead' in production until router lands."
    elif "summarize" in lowered or "information" in lowered or "deploy" in lowered:
        cards.append(
            {
                "type": "info_summary",
                "title": "Information inbox snapshot",
                "body": "Gap summaries, deploy health, and audit snippets — open the information column for full detail.",
                "source_app_id": "miche",
                "deep_link": "/#miche-information-inbox",
            }
        )
        reply = "Here's a summary card — depth stays in the information inbox."
    elif "htmlspec" in lowered or "focus" in lowered:
        cards.append(
            {
                "type": "focus_cta",
                "title": "Open htmlspec in Focus",
                "body": "Deep review needs full app chrome.",
                "source_app_id": "caffenagent",
                "focus_route": "/orchestrate",
            }
        )
        needs_focus = True
        suggested_focus = {
            "app_id": "caffenagent",
            "route": "/orchestrate",
            "reason": "htmlspec depth",
        }
        reply = "Use the Focus CTA below — I won't auto-redirect."

    return {
        "utterance_id": utterance_id,
        "reply_markdown": reply,
        "inline_cards": cards,
        "suggested_focus": suggested_focus,
        "needs_focus": needs_focus,
        "router_mode": "cassette",
        "latency_ms": 12,
    }


def route_utterance(
    *,
    utterance_id: str,
    text: str | None = None,
    audio_blob_id: str | None = None,
    source: str = "island",
    audit_path: Path | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    mode = router_mode()
    body_text = (text or "").strip()

    if mode == "cassette":
        result = _cassette_reply(text=body_text or "(voice)", utterance_id=utterance_id)
    else:
        result = {
            "utterance_id": utterance_id,
            "reply_markdown": "Production router not wired (SPR-06). Set MICHE_ISLAND_ROUTER_FIXTURE=cassette for dev.",
            "inline_cards": [],
            "needs_focus": False,
            "router_mode": "production_unavailable",
            "latency_ms": int((time.monotonic() - started) * 1000),
        }

    latency_ms = int((time.monotonic() - started) * 1000)
    result["latency_ms"] = latency_ms
    if latency_ms > 5000:
        result["timeout_badge"] = True

    audit = {
        "utterance_id": utterance_id,
        "text": body_text or None,
        "audio_blob_id": audio_blob_id,
        "source": source,
        "needs_focus": result.get("needs_focus", False),
        "router_mode": result.get("router_mode", mode),
        "latency_ms": latency_ms,
        "created_at": _iso_now(),
    }
    _append_utterance_audit(audit, path=audit_path)
    return result


def new_utterance_id() -> str:
    return str(uuid.uuid4())