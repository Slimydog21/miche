"""MPLAT-SPR-03 — action inbox aggregator and adapter."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from miche.adapters.caffenagent_actions import fetch_caffenagent_actions
from miche.inbox.action import ActionInboxAggregator, AppFetchResult
from miche.registry import AppRegistration, AppRegistry
from miche.web import create_app


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pr_fixture() -> dict:
    return {
        "action_id": str(uuid.uuid4()),
        "title": "PR #42 awaiting approval",
        "detail": "caffenagent gap loop",
        "severity": "blocking",
        "source_app": "caffenagent",
        "stale": False,
        "focus_deep_link": "/orchestrate",
        "created_at": _iso(),
    }


@pytest.fixture
def client():
    return TestClient(create_app())


def test_aggregator_ttl_cache_hit():
    calls = {"n": 0}

    def fetcher(app: AppRegistration) -> AppFetchResult:
        calls["n"] += 1
        return AppFetchResult(app_id=app.id, ok=True, items=[_pr_fixture()])

    reg = AppRegistry(
        version="1",
        install_profile="test",
        apps=[AppRegistration(id="caffenagent", display_name="CAI", enabled=True, base_url_env="X")],
        source_path="test",
    )
    agg = ActionInboxAggregator(registry=reg, fetcher=fetcher, ttl_seconds=120, now=lambda: 1000.0)
    snap1 = agg.collect()
    snap2 = agg.collect()
    assert snap2.cache_hit is True
    assert calls["n"] == 1
    snap3 = agg.collect(force=True)
    assert snap3.cache_hit is False
    assert calls["n"] == 2


def test_aggregator_sort_stable():
    items = [
        {
            "action_id": str(uuid.uuid4()),
            "title": "nit task",
            "severity": "nit",
            "source_app": "caffenagent",
            "stale": False,
            "created_at": "2026-06-01T10:00:00+00:00",
        },
        {
            "action_id": str(uuid.uuid4()),
            "title": "blocking task",
            "severity": "blocking",
            "source_app": "caffenagent",
            "stale": False,
            "created_at": "2026-06-02T10:00:00+00:00",
        },
    ]

    def fetcher(app: AppRegistration) -> AppFetchResult:
        return AppFetchResult(app_id=app.id, ok=True, items=items)

    reg = AppRegistry(
        version="1",
        install_profile="test",
        apps=[AppRegistration(id="caffenagent", display_name="CAI", enabled=True, base_url_env="X")],
        source_path="test",
    )
    agg = ActionInboxAggregator(registry=reg, fetcher=fetcher, ttl_seconds=60)
    snap1 = agg.collect()
    snap2 = agg.collect()
    assert [i["title"] for i in snap1.items] == [i["title"] for i in snap2.items]
    assert snap1.items[0]["severity"] == "blocking"


def test_per_app_503_does_not_fake_empty_inbox():
    def fetcher(app: AppRegistration) -> AppFetchResult:
        if app.id == "caffenagent":
            return AppFetchResult(app_id=app.id, ok=False, error="HTTP 503", stale=True)
        row = _pr_fixture()
        row["source_app"] = app.id
        row["title"] = f"{app.display_name} task"
        return AppFetchResult(app_id=app.id, ok=True, items=[row])

    reg = AppRegistry(
        version="1",
        install_profile="test",
        apps=[
            AppRegistration(id="caffenagent", display_name="CAI", enabled=True, base_url_env="X"),
            AppRegistration(id="friend", display_name="Friend", enabled=True, base_url_env="Y"),
        ],
        source_path="test",
    )
    agg = ActionInboxAggregator(registry=reg, fetcher=fetcher)
    snap = agg.collect(force=True)
    assert any(i.get("stale") for i in snap.items)
    assert any(i["source_app"] == "caffenagent" for i in snap.items)
    assert any(i["source_app"] == "friend" for i in snap.items)


def test_caffenagent_adapter_maps_pr_fixture():
    app = AppRegistration(
        id="caffenagent",
        display_name="CAI",
        enabled=True,
        base_url_env="CAFFENAGENT_PUBLIC_BASE_URL",
        focus_route="/orchestrate",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/inbox/actions":
            return httpx.Response(200, json={"items": [_pr_fixture()]})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://caffenagent.test")
    with patch.dict("os.environ", {"CAFFENAGENT_PUBLIC_BASE_URL": "http://caffenagent.test"}):
        result = fetch_caffenagent_actions(app, client=client)
    assert result.ok is True
    assert len(result.items) == 1
    assert result.items[0]["title"] == "PR #42 awaiting approval"


def test_api_platform_inbox_actions(client, monkeypatch):
    fixture = _pr_fixture()

    def fake_collect(*, force: bool = False):
        return {
            "ok": True,
            "items": [fixture],
            "apps": [{"app_id": "caffenagent", "ok": True, "stale": False, "count": 1}],
            "fetched_at": _iso(),
            "cache_hit": False,
        }

    monkeypatch.setattr("miche.routes.inbox.get_action_inbox", lambda force=False: fake_collect(force=force))
    r = client.get("/api/platform/inbox/actions")
    assert r.status_code == 200
    body = r.json()
    assert body["items"][0]["severity"] == "blocking"


def test_home_shows_degraded_app_not_fake_empty(client):
    with patch.dict("os.environ", {}, clear=True):
        r = client.get("/")
    assert r.status_code == 200
    assert "unreachable" in r.text.lower() or "env_unset" in r.text.lower()
    assert 'data-empty="false"' in r.text


def test_home_renders_action_row_with_focus_link(client, monkeypatch):
    fixture = _pr_fixture()

    class FakeSnap:
        items = [fixture]
        apps = []

    monkeypatch.setattr(
        "miche.routes.home._action_aggregator",
        MagicMock(collect=MagicMock(return_value=FakeSnap)),
    )
    r = client.get("/")
    assert r.status_code == 200
    assert "PR #42 awaiting approval" in r.text
    assert 'data-inbox-row' in r.text
    assert 'data-focus-deep-link="/orchestrate"' in r.text
    assert "Open in Focus" in r.text