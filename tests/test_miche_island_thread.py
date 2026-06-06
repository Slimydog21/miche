"""MPLAT-SPR-05 — island thread API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from miche.island.thread import append_message, load_thread
from miche.web import create_app


def test_thread_empty(client=None):
    client = client or TestClient(create_app())
    r = client.get("/api/platform/island/thread")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert isinstance(body["messages"], list)


def test_thread_persists_messages(tmp_path, monkeypatch):
    log = tmp_path / "thread.jsonl"
    monkeypatch.setattr("miche.island.thread._THREAD_LOG", log)
    append_message(role="user", content="hello", utterance_id="u1", path=log)
    append_message(role="assistant", content="hi", utterance_id="u1", path=log)
    rows = load_thread(path=log)
    assert len(rows) == 2
    assert rows[0]["role"] == "user"


def test_thread_api_returns_last_50(tmp_path, monkeypatch):
    log = tmp_path / "thread.jsonl"
    monkeypatch.setattr("miche.island.thread._THREAD_LOG", log)
    for i in range(55):
        append_message(role="user", content=f"msg-{i}", path=log)
    client = TestClient(create_app())
    monkeypatch.setattr("miche.island.thread.load_thread", lambda **kw: load_thread(limit=50, path=log))
    r = client.get("/api/platform/island/thread")
    assert len(r.json()["messages"]) == 50