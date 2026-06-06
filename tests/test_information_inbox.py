"""MPLAT-SPR-04 — information inbox providers and adapter."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import jsonschema
import pytest
from fastapi.testclient import TestClient

from miche.adapters.caffenagent_information import fetch_caffenagent_information
from miche.inbox.information import (
    AuditProvider,
    DeployProvider,
    GapProvider,
    InformationInboxAggregator,
    InformationProvider,
    ProviderResult,
    validate_information_item,
)
from miche.registry import AppRegistration, AppRegistry
from miche.web import create_app

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "miche_information_item.json"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gap_report_fixture() -> dict:
    return {
        "parent_run_id": "run_gap_test",
        "gaps": [
            {
                "id": "gap-001",
                "severity": "major",
                "status": "open",
                "claim": "Voice intent requires tailscale attach",
                "counterclaim": "Child handoff does not reflect it",
                "sources": [
                    {
                        "kind": "voice_block",
                        "ref": "inbox/2026-06-04-voice.md",
                        "excerpt": "operator requires tailscale attach",
                    },
                    {"kind": "child_handoff", "ref": "SPR-A", "excerpt": "done"},
                ],
            }
        ],
    }


def _info_item(**overrides) -> dict:
    base = {
        "info_id": str(uuid.uuid4()),
        "kind": "gap_summary",
        "title": "Gap summary",
        "body": "Voice vs handoff tension",
        "block_id": "inbox/2026-06-04-voice.md",
        "source_app": "caffenagent",
        "provider": "gap",
        "relevance_score": 0.85,
        "stale": False,
        "degraded": False,
        "created_at": _iso(),
    }
    base.update(overrides)
    return base


@pytest.fixture
def schema():
    return json.loads(_SCHEMA_PATH.read_text())


@pytest.fixture
def client():
    return TestClient(create_app())


def test_schema_kinds(schema):
    for kind in ("gap_summary", "deploy_health", "audit_snippet"):
        jsonschema.validate(instance=_info_item(kind=kind), schema=schema)


def test_gap_adapter_items_pass_aggregator_validation():
    report = _gap_report_fixture()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/inbox/information":
            return httpx.Response(404)
        if request.url.path == "/api/gap/run_gap_test":
            return httpx.Response(200, json=report)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url="http://caffenagent.test")

    def fetcher(registry: AppRegistry) -> list[dict]:
        return fetch_caffenagent_information(
            base_url="http://caffenagent.test",
            parent_run_id="run_gap_test",
            client=http,
        )

    reg = AppRegistry(version="1", install_profile="t", apps=[], source_path="t")
    snap = InformationInboxAggregator(
        registry=reg,
        providers=[GapProvider(fetch_gap_items=fetcher)],
    ).collect(force=True)
    assert len(snap.items) == 1
    assert snap.items[0]["block_id"] == "inbox/2026-06-04-voice.md"


def test_gap_adapter_maps_block_id():
    report = _gap_report_fixture()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/inbox/information":
            return httpx.Response(404)
        if request.url.path == "/api/gap/run_gap_test":
            return httpx.Response(200, json=report)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://caffenagent.test")
    items = fetch_caffenagent_information(
        base_url="http://caffenagent.test",
        parent_run_id="run_gap_test",
        client=client,
    )
    assert len(items) == 1
    assert items[0]["kind"] == "gap_summary"
    assert items[0]["block_id"] == "inbox/2026-06-04-voice.md"


def test_gap_adapter_read_only_get():
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://caffenagent.test")
    fetch_caffenagent_information(base_url="http://caffenagent.test", client=client)
    assert methods == ["GET"]


def test_provider_exception_shows_degraded_card():
    class BoomProvider(InformationProvider):
        name = "boom"

        def collect(self, *, registry: AppRegistry) -> ProviderResult:
            raise RuntimeError("provider blew up")

    reg = AppRegistry(version="1", install_profile="t", apps=[], source_path="t")
    agg = InformationInboxAggregator(registry=reg, providers=[BoomProvider()])
    snap = agg.collect(force=True)
    assert len(snap.items) == 1
    assert snap.items[0]["degraded"] is True
    assert "provider blew up" in snap.items[0]["body"]


def test_deploy_unknown_skips_not_fake_green(monkeypatch):
    reg = AppRegistry(
        version="1",
        install_profile="t",
        apps=[
            AppRegistration(id="caffenagent", display_name="CAI", enabled=True, base_url_env="X"),
        ],
        source_path="t",
    )
    with patch.dict("os.environ", {}, clear=True):
        snap = InformationInboxAggregator(
            registry=reg,
            providers=[DeployProvider()],
        ).collect(force=True)
    assert snap.items == []


def test_deploy_probe_failure_not_healthy(monkeypatch):
    reg = AppRegistry(
        version="1",
        install_profile="t",
        apps=[
            AppRegistration(id="caffenagent", display_name="CAI", enabled=True, base_url_env="X"),
        ],
        source_path="t",
    )

    class FailProbe:
        ok = False
        latency_ms = None
        checked_at = _iso()
        reason = "connection refused"

    with patch.dict("os.environ", {"X": "http://localhost:9"}):
        monkeypatch.setattr("miche.inbox.information.probe_app", lambda app, use_cache=True: FailProbe)
        snap = InformationInboxAggregator(registry=reg, providers=[DeployProvider()]).collect(force=True)

    assert len(snap.items) == 1
    card = snap.items[0]
    assert card["kind"] == "deploy_health"
    assert card["degraded"] is True
    assert "probe failed" in card["body"].lower()
    assert "ok" not in card["title"].lower()


def test_information_ttl_cache_hit():
    calls = {"n": 0}

    def fetcher(registry: AppRegistry) -> list[dict]:
        calls["n"] += 1
        return [_info_item()]

    reg = AppRegistry(version="1", install_profile="t", apps=[], source_path="t")
    agg = InformationInboxAggregator(
        registry=reg,
        providers=[GapProvider(fetch_gap_items=fetcher)],
        ttl_seconds=120,
        now=lambda: 1000.0,
    )
    snap1 = agg.collect()
    snap2 = agg.collect()
    assert snap2.cache_hit is True
    assert calls["n"] == 1


def test_audit_provider_reads_last_jsonl_line(tmp_path, monkeypatch):
    audit_log = tmp_path / "miche_audit.jsonl"
    audit_log.write_text(
        json.dumps(
            {
                "title": "Miche routed intent",
                "body": "Dispatched stale sessions query",
                "block_id": "N/A",
                "source_app": "miche_platform",
                "created_at": _iso(),
            }
        )
        + "\n"
    )
    monkeypatch.setattr("miche.inbox.information._AUDIT_LOG", audit_log)
    reg = AppRegistry(version="1", install_profile="t", apps=[], source_path="t")
    snap = InformationInboxAggregator(registry=reg, providers=[AuditProvider()]).collect(force=True)
    assert len(snap.items) == 1
    assert snap.items[0]["kind"] == "audit_snippet"


def test_gap_block_id_na_when_no_voice_source():
    report = {
        "parent_run_id": "run_x",
        "gaps": [
            {
                "id": "gap-002",
                "severity": "minor",
                "status": "open",
                "claim": "overlap only",
                "sources": [{"kind": "overlap_event", "ref": "overlap.jsonl"}],
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/gap/run_x":
            return httpx.Response(200, json=report)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://caffenagent.test")
    items = fetch_caffenagent_information(
        base_url="http://caffenagent.test",
        parent_run_id="run_x",
        client=client,
    )
    assert items[0]["block_id"] == "N/A"


def test_information_sort_by_relevance():
    def fetcher(registry: AppRegistry) -> list[dict]:
        return [
            _info_item(title="nit", relevance_score=0.5),
            _info_item(title="blocker", relevance_score=0.95),
        ]

    reg = AppRegistry(version="1", install_profile="t", apps=[], source_path="t")
    agg = InformationInboxAggregator(
        registry=reg,
        providers=[GapProvider(fetch_gap_items=fetcher)],
    )
    snap = agg.collect(force=True)
    assert snap.items[0]["relevance_score"] == 0.95


def test_api_platform_information_inbox(client, monkeypatch):
    fixture = _info_item(title="Audit line")

    monkeypatch.setattr(
        "miche.routes.inbox.get_information_inbox",
        lambda force=False: {
            "ok": True,
            "items": [fixture],
            "providers": [{"provider": "audit", "ok": True, "count": 1}],
            "fetched_at": _iso(),
            "cache_hit": False,
        },
    )
    r = client.get("/api/platform/inbox/information")
    assert r.status_code == 200
    assert r.json()["items"][0]["block_id"] == fixture["block_id"]


def test_home_renders_information_with_citation(client, monkeypatch):
    fixture = _info_item(body="A" * 250)

    class FakeSnap:
        items = [fixture]
        providers = []

    monkeypatch.setattr(
        "miche.routes.home._info_aggregator",
        MagicMock(collect=MagicMock(return_value=FakeSnap)),
    )
    monkeypatch.setattr(
        "miche.routes.home._action_aggregator",
        MagicMock(collect=MagicMock(return_value=MagicMock(items=[], apps=[]))),
    )
    r = client.get("/")
    assert r.status_code == 200
    assert "block: inbox/2026-06-04-voice.md" in r.text
    assert 'data-expandable="true"' in r.text
    assert 'data-info-kind="gap_summary"' in r.text


def test_validate_information_item_requires_block_id():
    item = _info_item()
    validate_information_item(item)
    bad = _info_item()
    del bad["block_id"]
    with pytest.raises(jsonschema.ValidationError):
        validate_information_item(bad)