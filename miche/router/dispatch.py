"""Intent router dispatch — MPLAT-SPR-06."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from ..registry import AppRegistry, load_registry
from ..tenancy.profiles import active_profile_id
from .capability_map import CapabilityError, resolve_capability

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "miche_router_decision.json"
_ROUTER_LOG = Path("logs/miche_router_dispatch.jsonl")

# Locked cassette fixtures — 10 utterances (rigor §3)
CASSETTE_FIXTURES: dict[str, dict[str, Any]] = {
    "stale sessions": {
        "app_id": "caffenagent",
        "capability": "sessions",
        "args": {"filter": "stale"},
        "needs_focus": False,
        "card_type": "action_item",
        "card_title": "Stale sessions",
        "card_body": "Listing sessions from caffenagent registry.",
        "reply": "Found stale sessions — see the inline card.",
    },
    "list sessions": {
        "app_id": "caffenagent",
        "capability": "sessions",
        "args": {},
        "needs_focus": False,
        "card_type": "action_item",
        "card_title": "Session registry",
        "card_body": "GET /api/sessions/registry",
        "reply": "Sessions listed inline — stay on home.",
    },
    "open studio": {
        "app_id": "caffenagent",
        "capability": "studio",
        "args": {},
        "needs_focus": True,
        "card_type": "focus_cta",
        "card_title": "Open Session Studio",
        "card_body": "Studio needs full Focus chrome.",
        "reply": "Studio needs Focus — use the CTA; I will not auto-open.",
    },
    "pr queue": {
        "app_id": "caffenagent",
        "capability": "prcrouch",
        "args": {},
        "needs_focus": False,
        "card_type": "route_progress",
        "card_title": "PR queue",
        "card_body": "Dispatch to caffenagent prcrouch capability.",
        "reply": "PR queue routed inline.",
    },
    "htmlspec": {
        "app_id": "caffenagent",
        "capability": "htmlspec",
        "args": {},
        "needs_focus": True,
        "card_type": "focus_cta",
        "card_title": "Open htmlspec",
        "card_body": "Deep spec work needs Focus.",
        "reply": "Use Focus CTA for htmlspec depth.",
    },
    "what is blocked": {
        "app_id": "caffenagent",
        "capability": "sessions",
        "args": {"triage": "action_inbox"},
        "needs_focus": False,
        "card_type": "action_item",
        "card_title": "Action triage",
        "card_body": "Pull must-do items before dispatching apps.",
        "reply": "Triage action inbox first.",
    },
    "deploy health": {
        "app_id": "caffenagent",
        "capability": "htmlspec",
        "args": {"view": "information"},
        "needs_focus": False,
        "card_type": "info_summary",
        "card_title": "Deploy health",
        "card_body": "Information inbox carries deploy snapshots.",
        "reply": "Deploy health summary inline.",
    },
    "egghead gap": {
        "app_id": "caffenagent",
        "capability": "prcrouch",
        "args": {"mode": "gap_review"},
        "needs_focus": False,
        "card_type": "route_progress",
        "card_title": "Gap review dispatch",
        "card_body": "Would invoke prcrouch for adversarial review.",
        "reply": "Gap review queued — progress card below.",
    },
    "hello miche": {
        "app_id": "caffenagent",
        "capability": "sessions",
        "args": {},
        "needs_focus": False,
        "card_type": None,
        "reply": "I'm on the island — ask about sessions, studio, or inbox triage.",
    },
    "maybe open something": {
        "app_id": "caffenagent",
        "capability": "sessions",
        "args": {},
        "needs_focus": False,
        "card_type": None,
        "reply": "Too vague for Focus — tell me studio, htmlspec, or sessions explicitly.",
    },
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_router_log() -> Path:
    override = os.environ.get("MICHE_ROUTER_DISPATCH_LOG", "").strip()
    if override:
        return Path(override)
    return _ROUTER_LOG


def router_log_path() -> Path:
    return _default_router_log()


def dispatch_mode() -> str:
    """Honest router modes: cassette (offline tests) or rules_v0 (keyword classifier)."""
    if os.environ.get("MICHE_ROUTER_FIXTURE", "").strip().lower() == "cassette":
        return "cassette"
    if os.environ.get("MICHE_ISLAND_ROUTER_FIXTURE", "").strip().lower() == "cassette":
        return "cassette"
    return "rules_v0"


def _utterance_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


def validate_decision(decision: dict[str, Any]) -> None:
    jsonschema.validate(instance=decision, schema=_load_schema())


def _append_audit(row: dict[str, Any], *, path: Path | None = None) -> None:
    log = path or _default_router_log()
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


def _blocked_inbox_decision(
    *,
    utterance_id: str,
    text: str,
    mode: str,
    latency_ms: int,
) -> dict[str, Any]:
    cards, reply = _action_inbox_cards()
    decision_id = str(uuid.uuid4())
    decision = {
        "router_decision_id": decision_id,
        "utterance_id": utterance_id,
        "utterance_hash": _utterance_hash(text),
        "app_id": "miche",
        "capability": "inbox_action",
        "args": {},
        "needs_focus": False,
        "inline_card": cards[0] if cards else None,
        "reply_markdown": reply,
        "router_mode": mode,
        "latency_ms": latency_ms,
    }
    validate_decision(decision)
    return {**decision, "inline_cards": cards, "suggested_focus": None, "invoke": "inbox://action"}


def _match_cassette(text: str) -> dict[str, Any] | None:
    lowered = text.lower().strip()
    for key, fixture in CASSETTE_FIXTURES.items():
        if key in lowered:
            return fixture
    return None


def _match_production(text: str) -> dict[str, Any] | None:
    """Registry-constrained classifier (non-cassette production path)."""
    lowered = text.lower()
    if "studio" in lowered and "open" in lowered:
        return CASSETTE_FIXTURES["open studio"]
    if "stale" in lowered and "session" in lowered:
        return CASSETTE_FIXTURES["stale sessions"]
    if "session" in lowered:
        return CASSETTE_FIXTURES["list sessions"]
    if "prcrouch" in lowered or " pr " in f" {lowered} " or lowered.startswith("pr "):
        return CASSETTE_FIXTURES["pr queue"]
    if "htmlspec" in lowered:
        return CASSETTE_FIXTURES["htmlspec"]
    if "blocked" in lowered and "session" not in lowered:
        return None
    if "deploy" in lowered:
        return CASSETTE_FIXTURES["deploy health"]
    if "gap" in lowered or "egghead" in lowered:
        return CASSETTE_FIXTURES["egghead gap"]
    if len(lowered.split()) <= 3:
        return CASSETTE_FIXTURES["maybe open something"]
    return CASSETTE_FIXTURES["hello miche"]


def _build_inline_card(
    fixture: dict[str, Any],
    *,
    resolved_invoke: str,
    focus_route: str | None = None,
) -> dict[str, Any] | None:
    card_type = fixture.get("card_type")
    if not card_type:
        return None
    card: dict[str, Any] = {
        "type": card_type,
        "title": fixture.get("card_title") or fixture["capability"],
        "body": fixture.get("card_body") or resolved_invoke,
        "source_app_id": fixture["app_id"],
    }
    if card_type == "focus_cta":
        card["focus_route"] = focus_route or fixture.get("focus_route") or "/orchestrate"
    return card


def _fixture_to_decision(
    *,
    utterance_id: str,
    text: str,
    fixture: dict[str, Any],
    mode: str,
    latency_ms: int,
    registry: AppRegistry | None = None,
) -> dict[str, Any]:
    resolved = resolve_capability(fixture["app_id"], fixture["capability"], registry=registry)
    inline_card = _build_inline_card(
        fixture,
        resolved_invoke=resolved.invoke,
        focus_route=resolved.focus_route,
    )
    inline_cards = [inline_card] if inline_card else []

    needs_focus = bool(fixture.get("needs_focus", False))
    suggested_focus = None
    if needs_focus and resolved.focus_route:
        suggested_focus = {
            "app_id": resolved.app_id,
            "route": resolved.focus_route,
            "reason": f"{resolved.capability} depth",
        }

    decision_id = str(uuid.uuid4())
    decision = {
        "router_decision_id": decision_id,
        "utterance_id": utterance_id,
        "utterance_hash": _utterance_hash(text),
        "app_id": resolved.app_id,
        "capability": resolved.capability,
        "args": fixture.get("args") or {},
        "needs_focus": needs_focus,
        "reply_markdown": fixture.get("reply") or "Routed.",
        "router_mode": mode,
        "latency_ms": latency_ms,
    }
    if inline_card is not None:
        decision["inline_card"] = inline_card
    validate_decision(decision)

    return {
        **decision,
        "inline_cards": inline_cards,
        "suggested_focus": suggested_focus,
        "invoke": resolved.invoke,
    }


def dispatch_utterance(
    *,
    utterance_id: str,
    text: str,
    source: str = "island",
    audit_path: Path | None = None,
    force_app_id: str | None = None,
    force_capability: str | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    body = (text or "").strip()
    if not body:
        raise ValueError("text required")

    mode = dispatch_mode()
    registry = load_registry()

    if force_app_id and force_capability:
        resolve_capability(force_app_id, force_capability, registry=registry)
        fixture = {
            "app_id": force_app_id,
            "capability": force_capability,
            "args": {},
            "needs_focus": False,
            "card_type": "route_progress",
            "card_title": f"{force_app_id}.{force_capability}",
            "card_body": "Explicit capability dispatch.",
            "reply": f"Dispatched {force_app_id}.{force_capability}.",
        }
    elif mode == "cassette":
        fixture = _match_cassette(body)
        if not fixture:
            fixture = CASSETTE_FIXTURES["hello miche"]
    else:
        fixture = _match_production(body)
        if fixture is None:
            latency_ms = int((time.monotonic() - started) * 1000)
            fallback_mode = "inbox_fallback"
            result = _blocked_inbox_decision(
                utterance_id=utterance_id,
                text=body,
                mode=fallback_mode,
                latency_ms=latency_ms,
            )
            audit = {
                "router_decision_id": result["router_decision_id"],
                "utterance_id": utterance_id,
                "utterance_hash": result["utterance_hash"],
                "text": body,
                "source": source,
                "profile_id": active_profile_id(),
                "app_id": result["app_id"],
                "capability": result["capability"],
                "needs_focus": False,
                "router_mode": fallback_mode,
                "latency_ms": latency_ms,
                "created_at": _iso_now(),
            }
            _append_audit(audit, path=audit_path)
            return result

    latency_ms = int((time.monotonic() - started) * 1000)
    result = _fixture_to_decision(
        utterance_id=utterance_id,
        text=body,
        fixture=fixture,
        mode=mode,
        latency_ms=latency_ms,
        registry=registry,
    )

    audit = {
        "router_decision_id": result["router_decision_id"],
        "utterance_id": utterance_id,
        "utterance_hash": result["utterance_hash"],
        "text": body,
        "source": source,
        "profile_id": active_profile_id(),
        "app_id": result["app_id"],
        "capability": result["capability"],
        "needs_focus": result["needs_focus"],
        "router_mode": mode,
        "latency_ms": latency_ms,
        "created_at": _iso_now(),
    }
    _append_audit(audit, path=audit_path)
    return result


def dispatch_for_island(
    *,
    utterance_id: str,
    text: str | None = None,
    audio_blob_id: str | None = None,
    source: str = "island",
    audit_path: Path | None = None,
) -> dict[str, Any]:
    """Adapter: island RouterResult shape from dispatch decision."""
    body_text = (text or "").strip()
    try:
        decision = dispatch_utterance(
            utterance_id=utterance_id,
            text=body_text or "(voice)",
            source=source,
            audit_path=audit_path,
        )
    except CapabilityError as exc:
        return {
            "utterance_id": utterance_id,
            "reply_markdown": f"Router rejected capability: {exc}",
            "inline_cards": [],
            "needs_focus": False,
            "router_mode": "error",
            "latency_ms": 0,
        }

    return {
        "utterance_id": utterance_id,
        "reply_markdown": decision["reply_markdown"],
        "inline_cards": decision.get("inline_cards") or [],
        "suggested_focus": decision.get("suggested_focus"),
        "needs_focus": decision["needs_focus"],
        "router_mode": decision["router_mode"],
        "latency_ms": decision["latency_ms"],
        "router_decision_id": decision["router_decision_id"],
        "audio_blob_id": audio_blob_id,
    }