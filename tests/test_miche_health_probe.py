"""MPLAT-SPR-01 — health probe tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from miche.health_probe import _PROBE_LOG, probe_app, probe_registry
from miche.registry import AppRegistration, CapabilityRegistration


@pytest.fixture
def probe_log(tmp_path, monkeypatch):
    path = tmp_path / "probe.jsonl"
    monkeypatch.setattr("miche.health_probe._PROBE_LOG", path)
    return path


def _app(**kwargs) -> AppRegistration:
    defaults = {
        "id": "caffenagent",
        "display_name": "CA",
        "enabled": True,
        "base_url_env": "CAFFENAGENT_PUBLIC_BASE_URL",
        "health_path": "/api/health",
        "capabilities": [CapabilityRegistration(id="sessions", invoke="GET /api/sessions/registry")],
        "focus_route": "/orchestrate",
    }
    defaults.update(kwargs)
    return AppRegistration(**defaults)


def test_env_unset_returns_ok_false(probe_log, monkeypatch):
    monkeypatch.delenv("CAFFENAGENT_PUBLIC_BASE_URL", raising=False)
    result = probe_app(_app())
    assert result.ok is False
    assert result.reason == "env_unset"


def test_success_probe(probe_log, monkeypatch):
    monkeypatch.setenv("CAFFENAGENT_PUBLIC_BASE_URL", "http://127.0.0.1:9999")

    class FakeResp:
        status_code = 200

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = FakeResp()

    result = probe_app(_app(), client=mock_client, use_cache=False)
    assert result.ok is True
    assert result.latency_ms is not None
    mock_client.get.assert_called_once_with("http://127.0.0.1:9999/api/health")


def test_failure_not_cached_as_success(probe_log, monkeypatch):
    monkeypatch.setenv("CAFFENAGENT_PUBLIC_BASE_URL", "http://127.0.0.1:9999")
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.ConnectError("refused")

    r1 = probe_app(_app(), client=mock_client, use_cache=False)
    r2 = probe_app(_app(), client=mock_client, use_cache=False)
    assert r1.ok is False
    assert r2.ok is False
    assert mock_client.get.call_count == 2


def test_success_cached_on_second_call(probe_log, monkeypatch):
    monkeypatch.setenv("CAFFENAGENT_PUBLIC_BASE_URL", "http://127.0.0.1:9999")

    class FakeResp:
        status_code = 200

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = FakeResp()

    r1 = probe_app(_app(), client=mock_client, use_cache=False)
    r2 = probe_app(_app(), client=mock_client, use_cache=True)
    assert r1.ok is True
    assert r2.ok is True
    assert mock_client.get.call_count == 1


def test_probe_registry_writes_jsonl(probe_log, monkeypatch):
    monkeypatch.delenv("CAFFENAGENT_PUBLIC_BASE_URL", raising=False)
    from miche.registry import load_registry

    results = probe_registry(load_registry())
    assert results
    lines = probe_log.read_text().strip().splitlines()
    assert lines
    row = json.loads(lines[-1])
    assert row["batch_size"] >= 1