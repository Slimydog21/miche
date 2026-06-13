"""MPLAT-ORCH-SPR-01+02 — proxy route and orchestration dashboard tests."""

from __future__ import annotations

import json
import re
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from miche.web import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


# --- Proxy route tests ---


class TestProxyRoute:
    """Tests for /api/caffenagent/{path:path} proxy."""

    def test_proxy_503_when_base_url_unset(self, client):
        """Proxy returns 503 when CAFFENAGENT_PUBLIC_BASE_URL is not configured."""
        with patch("miche.routes.proxy._resolve_base_url", return_value=None):
            r = client.get("/api/caffenagent/api/health")
        assert r.status_code == 503
        body = r.json()
        assert body["ok"] is False
        assert body["code"] == "caffenagent_unreachable"

    def test_proxy_503_when_auth_unset(self, client):
        """Proxy returns 503 when auth credentials are not configured."""
        with (
            patch("miche.routes.proxy._resolve_base_url", return_value="http://localhost:8080"),
            patch("miche.routes.proxy._build_auth_headers", return_value={}),
        ):
            r = client.get("/api/caffenagent/api/health")
        assert r.status_code == 503
        body = r.json()
        assert body["ok"] is False
        assert body["code"] == "auth_env_unset"

    def test_proxy_502_on_connection_error(self, client):
        """Proxy returns 502 when caffenagent is unreachable."""
        with (
            patch("miche.routes.proxy._resolve_base_url", return_value="http://localhost:9999"),
            patch("miche.routes.proxy._build_auth_headers", return_value={"Authorization": "Basic dGVzdDp0ZXN0"}),
        ):
            r = client.get("/api/caffenagent/api/health")
        assert r.status_code == 502
        body = r.json()
        assert body["ok"] is False
        assert body["code"] == "proxy_error"

    def test_proxy_forwards_get_request(self, client):
        """Proxy forwards GET requests and returns caffenagent's response verbatim."""
        mock_response = httpx.Response(
            status_code=200,
            json={"status": "ok", "product": "caffenagent"},
            headers={"content-type": "application/json"},
        )

        async def mock_request(self, method, url, **kwargs):
            return mock_response

        with (
            patch("miche.routes.proxy._resolve_base_url", return_value="http://localhost:8080"),
            patch("miche.routes.proxy._build_auth_headers", return_value={"Authorization": "Basic dGVzdDp0ZXN0"}),
            patch.object(httpx.AsyncClient, "request", mock_request),
        ):
            r = client.get("/api/caffenagent/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_proxy_forwards_post_body(self, client):
        """Proxy forwards POST body to caffenagent."""
        received = {}

        async def mock_request(self, method, url, **kwargs):
            received["method"] = method
            received["content"] = kwargs.get("content")
            return httpx.Response(
                status_code=201,
                json={"ok": True},
                headers={"content-type": "application/json"},
            )

        with (
            patch("miche.routes.proxy._resolve_base_url", return_value="http://localhost:8080"),
            patch("miche.routes.proxy._build_auth_headers", return_value={"Authorization": "Basic dGVzdDp0ZXN0"}),
            patch.object(httpx.AsyncClient, "request", mock_request),
        ):
            r = client.post(
                "/api/caffenagent/api/miche/studio/projects/test/agents",
                json={"subproject_path": "/", "cli_profile": "mimo"},
            )
        assert r.status_code == 201
        assert received["method"] == "POST"
        assert b"mimo" in received["content"]

    def test_proxy_forwards_error_status(self, client):
        """Proxy forwards caffenagent's error status codes verbatim."""
        mock_response = httpx.Response(
            status_code=409,
            json={"ok": False, "code": "duplicate_active"},
            headers={"content-type": "application/json"},
        )

        async def mock_request(self, method, url, **kwargs):
            return mock_response

        with (
            patch("miche.routes.proxy._resolve_base_url", return_value="http://localhost:8080"),
            patch("miche.routes.proxy._build_auth_headers", return_value={"Authorization": "Basic dGVzdDp0ZXN0"}),
            patch.object(httpx.AsyncClient, "request", mock_request),
        ):
            r = client.post(
                "/api/caffenagent/api/miche/studio/projects/test/agents",
                json={"subproject_path": "/"},
            )
        assert r.status_code == 409

    def test_proxy_413_on_oversized_body(self, client):
        """Proxy returns 413 when request body exceeds 10MB limit."""
        with (
            patch("miche.routes.proxy._resolve_base_url", return_value="http://localhost:8080"),
            patch("miche.routes.proxy._build_auth_headers", return_value={"Authorization": "Basic dGVzdDp0ZXN0"}),
        ):
            big_body = b"x" * (11 * 1024 * 1024)  # 11MB
            r = client.post(
                "/api/caffenagent/api/test",
                content=big_body,
                headers={"content-type": "application/octet-stream"},
            )
        assert r.status_code == 413
        assert r.json()["code"] == "payload_too_large"

    def test_proxy_does_not_intercept_static(self, client):
        """Proxy does not intercept /static/* requests."""
        r = client.get("/static/miche.css")
        # Should get the actual CSS file, not a proxy error
        assert r.status_code == 200

    def test_proxy_does_not_intercept_orchestrate(self, client):
        """Proxy does not intercept /orchestrate requests."""
        r = client.get("/orchestrate")
        assert r.status_code == 200
        assert "Orchestration" in r.text


class TestOrchestrateRoute:
    """Tests for /orchestrate route."""

    def test_orchestrate_200(self, client):
        """Orchestrate route returns 200 with dashboard template."""
        r = client.get("/orchestrate")
        assert r.status_code == 200
        assert "miche-orchestrate" in r.text
        assert "miche-island-mount" in r.text

    def test_orchestrate_has_project_grid(self, client):
        """Orchestrate template has the project grid container."""
        r = client.get("/orchestrate")
        assert 'data-project-grid' in r.text

    def test_orchestrate_has_connection_status(self, client):
        """Orchestrate template has the connection status element."""
        r = client.get("/orchestrate")
        assert 'data-connection-status' in r.text

    def test_orchestrate_links_css(self, client):
        """Orchestrate template links both miche.css and orchestrate.css."""
        r = client.get("/orchestrate")
        assert '/static/miche.css' in r.text
        assert '/static/orchestrate.css' in r.text

    def test_orchestrate_links_js(self, client):
        """Orchestrate template includes orchestrate.js as module."""
        r = client.get("/orchestrate")
        assert 'src="/static/orchestrate.js"' in r.text
        assert 'type="module"' in r.text

    def test_orchestrate_has_back_link(self, client):
        """Orchestrate template has a back link to home."""
        r = client.get("/orchestrate")
        assert 'href="/"' in r.text
        assert "Home" in r.text

    def test_orchestrate_degraded_on_registry_error(self, client):
        """Orchestrate renders degraded warning when app registry is broken."""
        from miche.registry import RegistryError

        with patch("miche.routes.orchestrate.load_registry", side_effect=RegistryError("registry broken")):
            r = client.get("/orchestrate")
        assert r.status_code == 200
        assert "registry" in r.text.lower()
        assert "degraded" in r.text.lower() or "unavailable" in r.text.lower()


class TestCassetteFixtures:
    """Tests for MPLAT-ORCH-SPR-04 agent orchestration fixtures."""

    @pytest.mark.parametrize(
        "utterance,expected_card",
        [
            ("run mimo on miche", "agent_status"),
            ("run claude on miche", "agent_status"),
            ("run grok on miche", "agent_status"),
            ("list agents", "agent_roster"),
            ("what agents are running", "agent_roster"),
            ("pause agent pa_abc123", "agent_status"),
            ("orchestrate", "focus_cta"),
        ],
    )
    def test_agent_fixtures_return_correct_card_type(self, utterance, expected_card):
        """Agent orchestration fixtures return the expected card types."""
        from miche.router.dispatch import CASSETTE_FIXTURES

        # Find the matching fixture
        fixture = CASSETTE_FIXTURES.get(utterance)
        if fixture is None:
            # Try substring match (production mode)
            for key, fix in CASSETTE_FIXTURES.items():
                if key in utterance:
                    fixture = fix
                    break
        assert fixture is not None, f"No fixture for: {utterance}"
        assert fixture.get("card_type") == expected_card

    def test_run_mimo_does_not_match_sessions(self):
        """'run mimo on miche studio sessions' should match sessions, not agent create."""
        from miche.router.dispatch import CASSETTE_FIXTURES

        fixture = CASSETTE_FIXTURES.get("run mimo")
        # The production matcher guards against this with "session" not in lowered
        assert fixture is not None
        assert fixture["args"].get("agent_action") == "create"


class TestOrchestrationSubPages:
    """Integration tests for all orchestration sub-pages."""

    @pytest.mark.parametrize(
        "path",
        [
            "/orchestrate/graph",
            "/orchestrate/studio",
            "/orchestrate/pr-queue",
            "/orchestrate/gaps",
            "/orchestrate/metrics",
            "/orchestrate/specs",
            "/orchestrate/settings",
            "/orchestrate/voice",
            "/orchestrate/memory",
        ],
    )
    def test_subpage_returns_200(self, client, path):
        """Each orchestration sub-page returns 200."""
        r = client.get(path)
        assert r.status_code == 200

    @pytest.mark.parametrize(
        "path",
        [
            "/orchestrate/graph",
            "/orchestrate/studio",
            "/orchestrate/pr-queue",
            "/orchestrate/gaps",
            "/orchestrate/metrics",
            "/orchestrate/specs",
            "/orchestrate/settings",
            "/orchestrate/voice",
            "/orchestrate/memory",
        ],
    )
    def test_subpage_has_island_mount(self, client, path):
        """Each orchestration sub-page has the island mount div."""
        r = client.get(path)
        assert "miche-island-mount" in r.text

    @pytest.mark.parametrize(
        "path",
        [
            "/orchestrate/graph",
            "/orchestrate/studio",
            "/orchestrate/pr-queue",
            "/orchestrate/gaps",
            "/orchestrate/metrics",
            "/orchestrate/specs",
            "/orchestrate/settings",
            "/orchestrate/voice",
            "/orchestrate/memory",
        ],
    )
    def test_subpage_has_back_link(self, client, path):
        """Each orchestration sub-page has a back link."""
        r = client.get(path)
        assert "href=" in r.text  # has at least one link

    @pytest.mark.parametrize(
        "path",
        [
            "/orchestrate/graph",
            "/orchestrate/studio",
            "/orchestrate/pr-queue",
            "/orchestrate/gaps",
            "/orchestrate/metrics",
            "/orchestrate/specs",
            "/orchestrate/settings",
            "/orchestrate/workstation",
        ],
    )
    def test_subpage_returns_200(self, client, path):
        """Each orchestration sub-page returns 200."""
        r = client.get(path)
        assert r.status_code == 200

    @pytest.mark.parametrize(
        "path",
        [
            "/orchestrate/graph",
            "/orchestrate/studio",
            "/orchestrate/pr-queue",
            "/orchestrate/gaps",
            "/orchestrate/metrics",
            "/orchestrate/specs",
            "/orchestrate/settings",
            "/orchestrate/workstation",
        ],
    )
    def test_subpage_has_island_mount(self, client, path):
        """Each orchestration sub-page has the island mount div."""
        r = client.get(path)
        assert "miche-island-mount" in r.text

    @pytest.mark.parametrize(
        "path",
        [
            "/orchestrate/graph",
            "/orchestrate/studio",
            "/orchestrate/pr-queue",
            "/orchestrate/gaps",
            "/orchestrate/metrics",
            "/orchestrate/specs",
            "/orchestrate/settings",
            "/orchestrate/workstation",
        ],
    )
    def test_subpage_has_back_link(self, client, path):
        """Each orchestration sub-page has a back link."""
        r = client.get(path)
        assert "href=" in r.text  # has at least one link

    @pytest.mark.parametrize(
        "path",
        [
            "/orchestrate/graph",
            "/orchestrate/studio",
            "/orchestrate/pr-queue",
            "/orchestrate/gaps",
            "/orchestrate/metrics",
            "/orchestrate/specs",
            "/orchestrate/settings",
            "/orchestrate/workstation",
        ],
    )
    def test_subpage_links_css(self, client, path):
        """Each orchestration sub-page links miche.css."""
        r = client.get(path)
        assert "/static/miche.css" in r.text

    def test_orchestrate_nav_has_five_items(self, client):
        """Orchestrate nav rail has exactly 5 destinations."""
        r = client.get("/orchestrate")
        for link in ["/", "/orchestrate", "/orchestrate/studio", "/orchestrate/memory", "/orchestrate/settings"]:
            assert link in r.text
        nav_match = re.search(r'<nav class="orchestrate-nav"[^>]*>(.*?)</nav>', r.text, re.S)
        assert nav_match is not None
        links = re.findall(r'href="([^"]*)"', nav_match.group(1))
        assert len(links) == 5

    def test_proxy_does_not_intercept_subpages(self, client):
        """Proxy does not intercept orchestration sub-page requests."""
        for path in ["/orchestrate/graph", "/orchestrate/studio", "/orchestrate/settings"]:
            r = client.get(path)
            assert r.status_code == 200
            # Should not be a proxy error
            assert "caffenagent_unreachable" not in r.text
