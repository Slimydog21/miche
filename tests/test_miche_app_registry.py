"""MPLAT-SPR-01 — app registry loader tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from miche.registry import RegistryError, load_registry

FIXTURES = Path(__file__).parent / "fixtures"


def test_default_registry_loads_caffenagent_enabled():
    reg = load_registry()
    assert reg.version == "1"
    ca = reg.get("caffenagent")
    assert ca is not None
    assert ca.enabled is True
    assert ca.base_url_env == "CAFFENAGENT_PUBLIC_BASE_URL"
    moomba = reg.get("moomba")
    assert moomba is not None
    assert moomba.enabled is False


def test_duplicate_id_raises_with_path():
    with pytest.raises(RegistryError) as exc:
        load_registry(FIXTURES / "registry_duplicate_id.yaml")
    assert "apps[1].id" in str(exc.value) or "duplicate" in str(exc.value).lower()


def test_enabled_without_base_url_env_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        """
version: "1"
apps:
  - id: solo
    display_name: Solo
    enabled: true
    focus_route: /solo
    capabilities:
      - id: x
        invoke: GET /x
"""
    )
    with pytest.raises(RegistryError) as exc:
        load_registry(bad)
    assert "base_url_env" in str(exc.value)


def test_focus_route_must_start_with_slash(tmp_path):
    bad = tmp_path / "focus.yaml"
    bad.write_text(
        """
version: "1"
apps:
  - id: solo
    display_name: Solo
    enabled: false
    focus_route: orchestrate
    capabilities: []
"""
    )
    with pytest.raises(RegistryError):
        load_registry(bad)


def test_public_dict_excludes_secrets():
    reg = load_registry()
    payload = reg.as_public_dict()
    raw = str(payload)
    assert "WEBHOOK_SECRET" not in raw
    assert payload["apps"][0]["capabilities"][0]["invoke"].startswith("GET ")