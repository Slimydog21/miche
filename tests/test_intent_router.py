"""MPLAT-SPR-06 — intent router dispatch + capability map."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from miche.router.capability_map import CapabilityError, resolve_capability
from miche.router.dispatch import (
    CASSETTE_FIXTURES,
    dispatch_utterance,
    validate_decision,
)
from miche.web import create_app

_SCHEMA = json.loads(
    Path(__file__).resolve().parent.parent.joinpath("schemas/miche_router_decision.json").read_text()
)

CASSETTE_UTTERANCES = list(CASSETTE_FIXTURES.keys())


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def router_log(tmp_path, monkeypatch):
    log = tmp_path / "router.jsonl"
    monkeypatch.setattr("miche.router.dispatch._ROUTER_LOG", log)
    monkeypatch.setenv("MICHE_ROUTER_FIXTURE", "cassette")
    monkeypatch.setenv("MICHE_ISLAND_ROUTER_FIXTURE", "cassette")
    return log


def test_schema_requires_needs_focus():
    with pytest.raises(jsonschema.ValidationError):
        validate_decision(
            {
                "router_decision_id": "00000000-0000-4000-8000-000000000001",
                "utterance_id": "u1",
                "utterance_hash": "a" * 64,
                "app_id": "caffenagent",
                "capability": "sessions",
                "args": {},
            }
        )


@pytest.mark.parametrize("utterance", CASSETTE_UTTERANCES)
def test_cassette_fixtures_locked(utterance, router_log):
    assert len(CASSETTE_UTTERANCES) == 10
    expected = CASSETTE_FIXTURES[utterance]
    result = dispatch_utterance(
        utterance_id=f"u-{utterance[:8]}",
        text=utterance,
        audit_path=router_log,
    )
    validate_decision({k: v for k, v in result.items() if k in _SCHEMA["required"] or k in _SCHEMA["properties"]})
    assert result["app_id"] == expected["app_id"]
    assert result["capability"] == expected["capability"]
    assert result["needs_focus"] == expected["needs_focus"]
    assert result["args"] == expected.get("args") or {}
    assert result["utterance_hash"]
    assert router_log.read_text().strip()


def test_production_blocked_uses_inbox(monkeypatch, router_log):
    monkeypatch.delenv("MICHE_ROUTER_FIXTURE", raising=False)
    monkeypatch.delenv("MICHE_ISLAND_ROUTER_FIXTURE", raising=False)
    monkeypatch.setattr("miche.router.dispatch._ROUTER_LOG", router_log)
    result = dispatch_utterance(
        utterance_id="u-blocked",
        text="what is blocked right now",
        audit_path=router_log,
    )
    assert result["app_id"] == "miche"
    assert result["capability"] == "inbox_action"


def test_stale_sessions_routes_to_sessions_list(router_log):
    result = dispatch_utterance(
        utterance_id="u-stale",
        text="any stale sessions?",
        audit_path=router_log,
    )
    assert result["app_id"] == "caffenagent"
    assert result["capability"] == "sessions"
    assert result["needs_focus"] is False
    assert result["inline_cards"]
    assert result["inline_cards"][0]["type"] == "action_item"


def test_open_studio_needs_focus(router_log):
    result = dispatch_utterance(
        utterance_id="u-studio",
        text="please open studio now",
        audit_path=router_log,
    )
    assert result["app_id"] == "caffenagent"
    assert result["capability"] == "studio"
    assert result["needs_focus"] is True
    assert any(c.get("type") == "focus_cta" for c in result["inline_cards"])


def test_vague_prompt_no_focus(router_log):
    result = dispatch_utterance(
        utterance_id="u-vague",
        text="maybe open something",
        audit_path=router_log,
    )
    assert result["needs_focus"] is False


def test_unknown_capability_returns_allowed_list(client):
    r = client.post(
        "/api/miche/router/dispatch",
        json={
            "utterance_id": "u-bad",
            "text": "dispatch",
            "app_id": "caffenagent",
            "capability": "nonexistent_capability",
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert "allowed_capabilities" in body["detail"]
    assert "sessions" in body["detail"]["allowed_capabilities"]


def test_resolve_capability_error():
    with pytest.raises(CapabilityError) as exc:
        resolve_capability("caffenagent", "bogus")
    assert "sessions" in exc.value.allowed


def test_dispatch_api_writes_audit(client, router_log, monkeypatch):
    monkeypatch.setattr("miche.router.dispatch._ROUTER_LOG", router_log)
    monkeypatch.setenv("MICHE_ROUTER_FIXTURE", "cassette")
    r = client.post(
        "/api/miche/router/dispatch",
        json={"utterance_id": "api-1", "text": "list sessions"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["router_decision_id"]
    audit = json.loads(router_log.read_text().strip().splitlines()[-1])
    assert audit["router_decision_id"] == body["router_decision_id"]
    assert audit["utterance_hash"] == body["utterance_hash"]


def test_production_mode_without_fixture(monkeypatch, router_log):
    monkeypatch.delenv("MICHE_ROUTER_FIXTURE", raising=False)
    monkeypatch.delenv("MICHE_ISLAND_ROUTER_FIXTURE", raising=False)
    monkeypatch.delenv("MICHE_ROUTER_LLM_API_KEY", raising=False)
    monkeypatch.setattr("miche.router.dispatch._ROUTER_LOG", router_log)
    result = dispatch_utterance(
        utterance_id="u-prod",
        text="open studio",
        audit_path=router_log,
    )
    assert result["router_mode"] == "production"
    assert result["needs_focus"] is True