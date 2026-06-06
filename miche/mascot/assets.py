"""Mascot asset loader — MPLAT-SPR-09."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
_CONTRACT_PATH = _PACKAGE_ROOT / "interfaces" / "miche_mascot.yaml"
_STATIC_ROOT = _PACKAGE_ROOT / "miche" / "static"

FORBIDDEN_LOOKALIKES = frozenset({"posthog_hedgehog", "disney_stitch", "hedgehog", "posthog"})


class AssetError(Exception):
    """Mascot asset invariant violation."""


def load_contract() -> dict[str, Any]:
    if not _CONTRACT_PATH.is_file():
        raise AssetError(f"mascot contract missing: {_CONTRACT_PATH}")
    data = yaml.safe_load(_CONTRACT_PATH.read_text())
    if not isinstance(data, dict):
        raise AssetError("mascot contract root must be a mapping")
    return data


def lint_forbidden_lookalikes(*, contract: dict[str, Any] | None = None) -> list[str]:
    """Rigor §1 — flag forbidden lookalike tokens in contract + static filenames."""
    data = contract or load_contract()
    violations: list[str] = []
    char = data.get("character") or {}
    for token in char.get("forbidden_lookalikes") or []:
        if str(token).lower() not in FORBIDDEN_LOOKALIKES:
            violations.append(f"unknown forbidden token: {token}")

    scan_roots = [_STATIC_ROOT, _STATIC_ROOT / "mascot"]
    for root in scan_roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            name = path.name.lower()
            for bad in FORBIDDEN_LOOKALIKES:
                if bad in name:
                    violations.append(f"forbidden filename fragment {bad!r} in {path}")
    return violations


def _public_url(relative: str) -> str:
    rel = relative.replace("\\", "/")
    if rel.startswith("miche/static/"):
        rel = rel[len("miche/static/") :]
    return f"/static/{rel.lstrip('/')}"


def resolve_sprite(
    persona_id: str,
    *,
    reduced_motion: bool = False,
    contract: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return sprite URLs with honest fallback (rigor §2 static path)."""
    data = contract or load_contract()
    base = data.get("base_asset") or {}

    static_rel = str(base.get("path") or "miche/static/mascot/miche-mascot-hero-static.png")
    svg_rel = str(base.get("fallback_svg") or "miche/static/miche-mascot.svg")

    static_path = _PACKAGE_ROOT / static_rel
    svg_path = _PACKAGE_ROOT / svg_rel

    sprite_path = static_path if static_path.is_file() else svg_path
    if not sprite_path.is_file():
        raise AssetError("no mascot sprite or fallback available")

    animated_url = _public_url(str(sprite_path.relative_to(_PACKAGE_ROOT)))
    if reduced_motion and static_path.is_file():
        static_url = _public_url(static_rel)
    elif static_path.is_file():
        static_url = _public_url(static_rel)
    else:
        static_url = _public_url(str(svg_path.relative_to(_PACKAGE_ROOT)))

    return {
        "sprite_url": static_url if reduced_motion else animated_url,
        "static_sprite_url": static_url,
        "asset_kind": "png" if sprite_path.suffix.lower() == ".png" else "svg",
    }


def hero_png_checksum() -> str:
    """Pinned hero PNG hash for tests (rigor §3)."""
    data = load_contract()
    rel = str((data.get("base_asset") or {}).get("path") or "")
    path = _PACKAGE_ROOT / rel
    if not path.is_file():
        raise AssetError(f"hero PNG missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()