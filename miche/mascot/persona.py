"""PersonaEngine — MPLAT-SPR-09."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .assets import load_contract, resolve_sprite

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
_VALID_CONTEXTS = frozenset({"home", "island"})
_RENDER_LOG = Path.home() / ".miche" / "logs" / "miche_persona_render.jsonl"

_CONTEXT_PERSONA = {
    "home": "engine",
    "island": "engine",
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def persona_render_log_path() -> Path:
    override = os.environ.get("MICHE_PERSONA_RENDER_LOG", "").strip()
    if override:
        return Path(override)
    return _RENDER_LOG


def _append_render_audit(row: dict[str, Any], *, path: Path | None = None) -> None:
    log = path or persona_render_log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as f:
        f.write(json.dumps(row) + "\n")


def _persona_record(persona_id: str, *, contract: dict[str, Any]) -> dict[str, Any]:
    for raw in contract.get("personas") or []:
        if str(raw.get("id")) == persona_id:
            return raw
    raise ValueError(f"unknown persona_id: {persona_id}")


def _pick_beverage(persona: dict[str, Any], *, context: str) -> str | None:
    beverages = persona.get("beverages") or {}
    flat: list[str] = []
    for group in beverages.values():
        flat.extend(str(b) for b in group or [])
    if not flat:
        return None
    idx = (hash(context) ^ hash(persona.get("id"))) % len(flat)
    return flat[idx]


def _animation_for_context(persona: dict[str, Any], *, context: str) -> str:
    states = persona.get("states") or {}
    if context == "home":
        return str(states.get("idle") or persona.get("default_animation") or "mug_wobble")
    return str(states.get("idle") or persona.get("default_animation") or "chug_cycle")


class PersonaEngine:
    def __init__(self, *, contract: dict[str, Any] | None = None) -> None:
        self._contract = contract or load_contract()

    def resolve(
        self,
        *,
        context: str,
        reduced_motion: bool = False,
        audit: bool = True,
        audit_path: Path | None = None,
    ) -> dict[str, Any]:
        ctx = (context or "").strip().lower()
        if ctx not in _VALID_CONTEXTS:
            raise ValueError(f"context must be one of {sorted(_VALID_CONTEXTS)}")

        persona_id = _CONTEXT_PERSONA.get(ctx, "engine")
        persona = _persona_record(persona_id, contract=self._contract)
        sprites = resolve_sprite(persona_id, reduced_motion=reduced_motion, contract=self._contract)
        animation_key = _animation_for_context(persona, context=ctx)
        beverage = _pick_beverage(persona, context=ctx)

        persona_render_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "ok": True,
            "context": ctx,
            "persona_id": persona_id,
            "persona_render_id": persona_render_id,
            "sprite_url": sprites["sprite_url"],
            "static_sprite_url": sprites["static_sprite_url"],
            "animation_key": animation_key,
            "reduced_motion": reduced_motion,
            "asset_kind": sprites["asset_kind"],
        }
        if beverage:
            payload["beverage"] = beverage

        if audit:
            _append_render_audit(
                {
                    "persona_render_id": persona_render_id,
                    "persona_id": persona_id,
                    "animation_key": animation_key,
                    "context": ctx,
                    "reduced_motion": reduced_motion,
                    "sprite_url": sprites["sprite_url"],
                    "created_at": _iso_now(),
                },
                path=audit_path,
            )
        return payload


def resolve_persona(
    *,
    context: str,
    reduced_motion: bool = False,
    audit_path: Path | None = None,
) -> dict[str, Any]:
    return PersonaEngine().resolve(context=context, reduced_motion=reduced_motion, audit_path=audit_path)