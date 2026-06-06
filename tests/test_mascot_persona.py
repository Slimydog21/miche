"""MPLAT-SPR-09 — mascot persona engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from miche.mascot.assets import (
    hero_png_checksum,
    lint_forbidden_lookalikes,
    load_contract,
    resolve_sprite,
)
from miche.mascot.persona import PersonaEngine, resolve_persona
from miche.web import create_app

_PINNED_HERO_SHA256 = "3b0899c33966da720b7da82b8582d6500130c4b7d2518e202b10274b2d2485d1"


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def persona_log(tmp_path, monkeypatch):
    log = tmp_path / "persona.jsonl"
    monkeypatch.setenv("MICHE_PERSONA_RENDER_LOG", str(log))
    return log


def test_contract_syncs_persona_ids():
    data = load_contract()
    ids = {str(p["id"]) for p in data.get("personas") or []}
    assert "engine" in ids
    assert "moomba" in ids
    assert data["character"]["forbidden_lookalikes"]


def test_forbidden_lookalikes_lint_clean():
    violations = lint_forbidden_lookalikes()
    assert violations == []


def test_hero_png_checksum_pinned():
    digest = hero_png_checksum()
    assert len(digest) == 64
    # Pin exact bytes of generated 48x48 accent PNG (rigor §3)
    assert digest == _PINNED_HERO_SHA256


def test_resolve_sprite_fallback_to_svg(monkeypatch, tmp_path):
    contract = load_contract()
    missing = tmp_path / "missing.png"
    contract = {**contract, "base_asset": {**contract["base_asset"], "path": str(missing)}}
    sprites = resolve_sprite("engine", contract=contract)
    assert sprites["sprite_url"].endswith(".svg")
    assert sprites["static_sprite_url"].endswith(".svg")


def test_persona_api_home_context(client, persona_log):
    r = client.get("/api/miche/persona", params={"context": "home"})
    assert r.status_code == 200
    body = r.json()
    assert body["persona_id"] == "engine"
    assert body["sprite_url"].startswith("/static/")
    assert body["animation_key"]
    assert body["persona_render_id"]
    assert persona_log.read_text().strip()


def test_persona_api_island_context(client):
    r = client.get("/api/miche/persona", params={"context": "island"})
    assert r.status_code == 200
    body = r.json()
    assert body["context"] == "island"
    assert "beverage" in body


def test_persona_api_reduced_motion_static_png(client):
    r = client.get("/api/miche/persona", params={"context": "home", "reduced_motion": True})
    assert r.status_code == 200
    body = r.json()
    assert body["reduced_motion"] is True
    assert body["sprite_url"].endswith(".png")


def test_persona_api_invalid_context(client):
    r = client.get("/api/miche/persona", params={"context": "studio"})
    assert r.status_code == 400


def test_persona_render_audit_fields(persona_log):
    row = resolve_persona(context="home", audit_path=persona_log)
    audit = json.loads(persona_log.read_text().strip())
    assert audit["persona_render_id"] == row["persona_render_id"]
    assert audit["persona_id"] == "engine"
    assert audit["animation_key"]
    assert audit["context"] == "home"


def test_home_html_has_mascot_mount(client):
    html = client.get("/").text
    assert 'id="miche-home-mascot"' in html
    assert "data-mascot-context" in html


def test_island_css_reduced_motion_guard():
    css = (Path(__file__).resolve().parent.parent / "miche/static/island.css").read_text()
    assert "prefers-reduced-motion" in css
    assert "miche-mascot-wobble" in css
    assert ".miche-island__pill[data-animation]" in css


def test_engine_default_persona():
    engine = PersonaEngine()
    payload = engine.resolve(context="home", audit=False)
    assert payload["persona_id"] == "engine"
    assert payload["animation_key"] in {"mug_wobble", "chug_cycle", "chug_1_2s"}