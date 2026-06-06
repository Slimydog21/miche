"""MPLAT-SPR-02 — home page shell layout contract."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from miche.registry import AppRegistration, AppRegistry, RegistryError
from miche.routes.home import MOUNT_ELEMENT_ID, _LAYOUT_VERSION, render_home
from miche.web import create_app

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_MICHE_CSS = _PACKAGE_ROOT / "miche" / "static" / "miche.css"
_HOME_JS = _PACKAGE_ROOT / "miche" / "static" / "home.js"


@pytest.fixture
def client():
    return TestClient(create_app())


def test_get_root_serves_home_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    html = r.text
    assert f'id="{MOUNT_ELEMENT_ID}"' in html
    assert f'content="{_LAYOUT_VERSION}"' in html
    assert f'data-layout-version="{_LAYOUT_VERSION}"' in html
    assert 'data-island-ready="false"' in html


def test_mount_id_frozen_in_js_and_layout_version_in_meta():
    js = _HOME_JS.read_text()
    assert f'"{MOUNT_ELEMENT_ID}"' in js
    ctx = render_home()
    assert ctx["layout_version"] == _LAYOUT_VERSION


def test_empty_inboxes_honest_no_demo_rows(client, monkeypatch):
    class EmptySnap:
        items = []
        apps = []

    monkeypatch.setattr(
        "miche.routes.home._action_aggregator",
        MagicMock(collect=MagicMock(return_value=EmptySnap)),
    )
    r = client.get("/")
    html = r.text.lower()
    assert "lorem ipsum" not in html
    assert 'data-empty="true"' in r.text
    assert "nothing queued yet" in html
    assert "no summaries yet" in html
    assert "capture voice on the island" in html
    assert 'data-inbox-row' not in r.text


def test_caffenagent_chip_when_registry_present(client):
    r = client.get("/")
    html = r.text
    assert 'data-app-id="caffenagent"' in html
    assert "Caffeine Agent" in html
    assert 'data-focus-route="/orchestrate"' in html
    assert "moomba" not in html.lower()


def test_no_chips_when_registry_has_no_focus_apps():
    reg = AppRegistry(
        version="1",
        install_profile="test_empty",
        apps=[
            AppRegistration(id="solo", display_name="Solo", enabled=True, focus_route=None),
        ],
        source_path="test",
    )
    ctx = render_home(registry=reg)
    assert ctx["app_chips"] == []


def test_home_degraded_when_registry_missing(client, tmp_path):
    missing = tmp_path / "missing_registry.yaml"
    with patch("miche.routes.home.load_registry", side_effect=RegistryError("registry not found")):
        r = client.get("/")
    assert r.status_code == 503
    assert "registry unavailable" in r.text.lower()
    assert f'id="{MOUNT_ELEMENT_ID}"' in r.text
    assert "miche-chip" not in r.text


def test_lemon_tokens_in_miche_css():
    css = _MICHE_CSS.read_text()
    for token in (
        "--color-primary:",
        "--color-accent:",
        "--shadow-card:",
        "--border:",
        "--font-sans:",
    ):
        assert token in css


def test_responsive_layout_css_contract():
    css = _MICHE_CSS.read_text()
    assert ".miche-main" in css
    assert re.search(r"\.miche-main\s*\{[^}]*grid-template-columns:\s*1fr\s*;", css, re.S)
    assert "@media (min-width: 768px)" in css
    assert re.search(
        r"@media \(min-width:\s*768px\)\s*\{[^}]*\.miche-main\s*\{[^}]*grid-template-columns:\s*1fr\s+1fr",
        css,
        re.S,
    )
    assert "@media (max-width: 390px)" in css
    assert "@media (min-width: 1280px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_static_assets_served(client):
    css = client.get("/static/miche.css")
    assert css.status_code == 200
    assert "--color-primary" in css.text
    js = client.get("/static/home.js")
    assert js.status_code == 200
    assert MOUNT_ELEMENT_ID in js.text
    assert 'dataset.islandReady = "shell"' in js.text