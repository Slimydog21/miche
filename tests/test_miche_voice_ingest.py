"""MPLAT-SPR-05 — island voice ingest."""

from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from miche.voice_ingest import has_asr_key, ingest_voice
from miche.web import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_asr_skipped_without_key(monkeypatch, tmp_path):
    monkeypatch.delenv("MICHE_ASR_API_KEY", raising=False)
    monkeypatch.setattr("miche.voice_ingest._VOICE_DIR", tmp_path)
    assert has_asr_key() is False
    result = ingest_voice(utterance_id="v1", audio_bytes=b"fake-audio")
    assert result["asr_status"] == "asr_skipped"
    assert result["transcript"] is None
    assert result["transcript"] is None
    assert "stub" in result["detail"].lower()
    assert "not a fake" in result["detail"].lower()


def test_voice_endpoint_stores_and_routes(client, tmp_path, monkeypatch):
    monkeypatch.setattr("miche.voice_ingest._VOICE_DIR", tmp_path / "voice")
    monkeypatch.setattr("miche.island.thread._THREAD_LOG", tmp_path / "thread.jsonl")
    monkeypatch.setattr("miche.island.router._UTTERANCE_LOG", tmp_path / "audit.jsonl")
    monkeypatch.setenv("MICHE_ISLAND_ROUTER_FIXTURE", "cassette")
    monkeypatch.delenv("MICHE_ASR_API_KEY", raising=False)

    r = client.post(
        "/api/platform/island/voice",
        data={"utterance_id": "voice-1"},
        files={"audio": ("voice.webm", BytesIO(b"\x00\x01\x02"), "audio/webm")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["voice"]["asr_status"] == "asr_skipped"
    assert body.get("route")