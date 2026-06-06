"""MPLAT-SPR-01 — platform apps API tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from miche.web import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_list_apps_includes_capabilities(client):
    r = client.get("/api/platform/apps")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["version"] == "1"
    apps = body["apps"]
    ca = next(a for a in apps if a["id"] == "caffenagent")
    assert ca["enabled"] is True
    cap_ids = {c["id"] for c in ca["capabilities"]}
    assert "sessions" in cap_ids
    assert "studio" in cap_ids
    assert "WEBHOOK" not in r.text


def test_app_health_env_unset(client):
    with patch.dict("os.environ", {}, clear=True):
        r = client.get("/api/platform/apps/caffenagent/health")
    assert r.status_code == 200
    health = r.json()["health"]
    assert health["ok"] is False
    assert health["reason"] == "env_unset"


def test_unknown_app_404(client):
    r = client.get("/api/platform/apps/unknown/health")
    assert r.status_code == 404