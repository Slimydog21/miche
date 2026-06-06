"""MPLAT-SPR-05 — island utterance routing + audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from miche.island.router import route_utterance, router_mode
from miche.web import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def audit_log(tmp_path, monkeypatch):
    log = tmp_path / "utterance.jsonl"
    monkeypatch.setattr("miche.island.router._UTTERANCE_LOG", log)
    monkeypatch.setenv("MICHE_ISLAND_ROUTER_FIXTURE", "cassette")
    return log


def test_router_cassette_mode(audit_log):
    assert router_mode() == "cassette"
    result = route_utterance(utterance_id="u-test", text="what is blocked", audit_path=audit_log)
    assert result["utterance_id"] == "u-test"
    assert result["inline_cards"]
    assert result["needs_focus"] is False
    lines = audit_log.read_text().strip().splitlines()
    assert len(lines) == 1
    audit = json.loads(lines[0])
    assert audit["utterance_id"] == "u-test"
    assert "needs_focus" in audit


def test_focus_cta_requires_explicit_needs_focus(audit_log):
    result = route_utterance(utterance_id="u2", text="open htmlspec", audit_path=audit_log)
    assert result["needs_focus"] is True
    assert any(c["type"] == "focus_cta" for c in result["inline_cards"])


def test_post_utterance_writes_thread_and_audit(client, tmp_path, monkeypatch):
    thread_log = tmp_path / "thread.jsonl"
    audit_log = tmp_path / "audit.jsonl"
    monkeypatch.setattr("miche.island.thread._THREAD_LOG", thread_log)
    monkeypatch.setattr("miche.island.router._UTTERANCE_LOG", audit_log)
    monkeypatch.setenv("MICHE_ISLAND_ROUTER_FIXTURE", "cassette")

    r = client.post(
        "/api/platform/island/utterance",
        json={"utterance_id": "uuid-1", "text": "any stale sessions?", "source": "island"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "reply_markdown" in body
    audit_line = json.loads(audit_log.read_text().strip().splitlines()[-1])
    assert audit_line["utterance_id"] == "uuid-1"
    assert audit_line["source"] == "island"
    assert "needs_focus" in audit_line
    assert audit_line["router_mode"] == "cassette"
    assert thread_log.read_text().count("uuid-1") >= 2


def test_info_summary_card_type(audit_log):
    result = route_utterance(utterance_id="u-info", text="summarize deploy health", audit_path=audit_log)
    assert any(c["type"] == "info_summary" for c in result["inline_cards"])


def test_timeout_badge_when_slow(monkeypatch, audit_log):
    times = iter([0.0, 0.0, 0.0, 6.0])

    def fake_monotonic():
        return next(times, 6.0)

    monkeypatch.setattr("miche.island.router.time.monotonic", fake_monotonic)
    monkeypatch.setattr("miche.router.dispatch.time.monotonic", fake_monotonic)
    result = route_utterance(utterance_id="u-slow", text="hello", audit_path=audit_log)
    assert result.get("timeout_badge") is True


def test_empty_utterance_rejected(client):
    r = client.post("/api/platform/island/utterance", json={"text": "  "})
    assert r.status_code == 400