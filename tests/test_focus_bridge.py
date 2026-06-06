"""MPLAT-SPR-07 — Focus mode bridge."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from miche.focus.handoff import (
    create_handoff,
    load_handoff,
    restore_payload,
    validate_handoff,
    validate_focus_path,
)
from miche.registry import AppRegistration, CapabilityRegistration, load_registry
from miche.web import create_app

_SCHEMA = json.loads(
    Path(__file__).resolve().parent.parent.joinpath("schemas/miche_focus_handoff.json").read_text()
)


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def handoff_store(tmp_path, monkeypatch):
    store = tmp_path / "handoffs.jsonl"
    monkeypatch.setattr("miche.focus.handoff._HANDOFF_STORE", store)
    return store


@pytest.fixture
def caffen_base(monkeypatch):
    monkeypatch.setenv("CAFFENAGENT_PUBLIC_BASE_URL", "https://caffenagent.example.test")


def test_schema_requires_return_url_and_island_state_token():
    with pytest.raises(jsonschema.ValidationError):
        validate_handoff(
            {
                "handoff_id": "00000000-0000-4000-8000-000000000001",
                "app_id": "caffenagent",
                "path": "/orchestrate",
                "expires_at": "2026-06-07T00:00:00+00:00",
            }
        )


def test_create_handoff_writes_audit(handoff_store, caffen_base):
    row = create_handoff(
        app_id="caffenagent",
        path="/studio",
        island_expanded=True,
        utterance_id="u-1",
        store_path=handoff_store,
    )
    validate_handoff(row)
    assert row["handoff_id"]
    assert row["island_state_token"]
    assert row["return_url"] == "/"
    assert row["island_expanded"] is True
    assert handoff_store.read_text().strip()


def test_open_redirect_rejected():
    app = load_registry().get("caffenagent")
    assert app is not None
    with pytest.raises(ValueError, match="open redirect"):
        validate_focus_path(app, "//evil.test/steal")


def test_path_traversal_rejected(caffen_base):
    app = load_registry().get("caffenagent")
    assert app is not None
    with pytest.raises(ValueError, match="traversal"):
        validate_focus_path(app, "/orchestrate/../studio")


def test_restore_collapsed_island_state(client, handoff_store, caffen_base):
    row = create_handoff(
        app_id="caffenagent",
        path="/orchestrate",
        island_expanded=False,
        store_path=handoff_store,
    )
    r = client.get(f"/api/platform/focus/restore?handoff_id={row['handoff_id']}")
    assert r.json()["island_expanded"] is False


def test_unknown_path_rejected(caffen_base):
    app = load_registry().get("caffenagent")
    assert app is not None
    with pytest.raises(ValueError, match="not allowed"):
        validate_focus_path(app, "/not-a-real-route")


def test_focus_degraded_without_base_url(client, handoff_store, monkeypatch):
    monkeypatch.delenv("CAFFENAGENT_PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr("miche.focus.handoff._HANDOFF_STORE", handoff_store)
    r = client.get("/focus/caffenagent?path=/orchestrate")
    assert r.status_code == 200
    assert "base URL is not configured" in r.text
    assert "← Miche home" in r.text
    assert 'data-embed-mode="degraded"' in r.text or 'data-embed-mode="degraded"' in r.text.replace("'", '"')


def test_focus_navigate_redirect_when_embed_disabled(client, handoff_store, caffen_base, monkeypatch):
    monkeypatch.setattr("miche.focus.handoff._HANDOFF_STORE", handoff_store)
    r = client.get("/focus/caffenagent?path=/studio", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].startswith("https://caffenagent.example.test/studio")
    assert "miche_handoff=" in r.headers["location"]


def test_focus_iframe_when_embed_allowed(client, handoff_store, caffen_base, monkeypatch):
    monkeypatch.setattr("miche.focus.handoff._HANDOFF_STORE", handoff_store)

    def fake_load(path=None):
        reg = load_registry(path=path)
        apps = []
        for app in reg.apps:
            if app.id == "caffenagent":
                apps.append(
                    AppRegistration(
                        id=app.id,
                        display_name=app.display_name,
                        enabled=True,
                        base_url_env=app.base_url_env,
                        capabilities=app.capabilities,
                        focus_route=app.focus_route,
                        focus_paths=["/orchestrate", "/studio"],
                        focus_embed_allowed=True,
                    )
                )
            else:
                apps.append(app)
        from miche.registry import AppRegistry

        return AppRegistry(
            version=reg.version,
            install_profile=reg.install_profile,
            apps=apps,
            source_path=reg.source_path,
        )

    monkeypatch.setattr("miche.focus.handoff.load_registry", fake_load)
    monkeypatch.setattr("miche.routes.focus.load_registry", fake_load)
    r = client.get("/focus/caffenagent?path=/studio")
    assert r.status_code == 200
    assert "<iframe" in r.text
    assert "sandbox=" in r.text


def test_restore_api_returns_island_state(client, handoff_store, caffen_base):
    row = create_handoff(
        app_id="caffenagent",
        path="/orchestrate",
        island_expanded=True,
        store_path=handoff_store,
    )
    r = client.get(f"/api/platform/focus/restore?handoff_id={row['handoff_id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["island_expanded"] is True
    assert body["island_state_token"] == row["island_state_token"]


def test_expired_handoff_not_restored(handoff_store, caffen_base):
    row = create_handoff(
        app_id="caffenagent",
        path="/orchestrate",
        store_path=handoff_store,
    )
    expired = dict(row)
    expired["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    handoff_store.write_text(json.dumps(expired) + "\n")
    assert load_handoff(row["handoff_id"], store_path=handoff_store) is None
    assert restore_payload(row["handoff_id"], store_path=handoff_store) is None


def test_handoff_ttl_24h(handoff_store, caffen_base):
    row = create_handoff(app_id="caffenagent", path="/sessions", store_path=handoff_store)
    expires = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
    delta = expires - created
    assert 23 <= delta.total_seconds() / 3600 <= 25


def test_unknown_app_404(client):
    r = client.get("/focus/not-real")
    assert r.status_code == 404


def test_registry_documents_focus_paths():
    app = load_registry().get("caffenagent")
    assert app is not None
    assert "/orchestrate" in app.focus_paths
    assert "/studio" in app.focus_paths
    assert "/sessions" in app.focus_paths
    assert app.focus_embed_allowed is False