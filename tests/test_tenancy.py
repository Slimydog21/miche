"""MPLAT-SPR-08 — multi-tenant install profiles."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import jsonschema
import pytest

from miche.registry import RegistryError, load_registry
from miche.router.capability_map import CapabilityError, resolve_capability
from miche.island.router import route_utterance
from miche.router.dispatch import dispatch_utterance
from miche.routes.home import render_home
from miche.tenancy.profiles import (
    ProfileError,
    active_profile_id,
    apply_active_profile,
    load_install_profile,
    validate_secrets_path,
)
from miche.web import create_app
from fastapi.testclient import TestClient

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_SCHEMA = json.loads(
    Path(__file__).resolve().parent.parent.joinpath("schemas/miche_install_profile.json").read_text()
)
_FRIEND_REGISTRY = _FIXTURES / "registry_friend.yaml"


@pytest.fixture
def client():
    return TestClient(create_app())


def test_install_profile_schema_requires_fields():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"profile_id": "x"}, schema=_SCHEMA)


def test_operator_default_profile_loads():
    profile = load_install_profile("operator_default")
    assert profile.profile_id == "operator_default"
    assert "caffenagent" in profile.apps
    assert profile.secrets_path.endswith("operator_default/secrets.env")


def test_default_operator_registry_unchanged(monkeypatch):
    monkeypatch.delenv("MICHE_PROFILE", raising=False)
    reg = load_registry()
    assert reg.install_profile == "operator_default"
    assert reg.get("caffenagent") is not None
    assert reg.get("caffenagent").operator_only is True


def test_friend_profile_filters_operator_apps(monkeypatch):
    monkeypatch.setenv("MICHE_PROFILE", "friend")
    reg = load_registry(path=_FRIEND_REGISTRY)
    assert reg.install_profile == "friend"
    assert reg.get("caffenagent") is None
    assert reg.get("moomba") is not None


def test_profile_mixup_hard_fails(monkeypatch):
    monkeypatch.setenv("MICHE_PROFILE", "friend")
    raw = load_registry(path=Path(__file__).resolve().parent.parent / "interfaces/miche_app_registry.yaml", skip_profile=True)
    with pytest.raises(ProfileError, match="profile mix-up"):
        apply_active_profile(raw)


def test_secrets_path_traversal_rejected():
    with pytest.raises(ProfileError, match="path traversal"):
        validate_secrets_path("~/.miche/profiles/friend/../operator_default/secrets.env", "friend")


def test_secrets_path_outside_profile_root_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("miche.tenancy.profiles._PROFILE_ROOT", tmp_path)
    outside = tmp_path / "elsewhere" / "secrets.env"
    outside.parent.mkdir(parents=True)
    outside.write_text("X=1\n")
    with pytest.raises(ProfileError, match="must stay under"):
        validate_secrets_path(str(outside), "friend")


def test_operator_corpus_path_forbidden(tmp_path, monkeypatch):
    monkeypatch.setattr("miche.tenancy.profiles._PROFILE_ROOT", tmp_path)
    bad = tmp_path / "friend" / "operator-corpus" / "secrets.env"
    bad.parent.mkdir(parents=True)
    with pytest.raises(ProfileError, match="operator corpus"):
        validate_secrets_path(str(bad), "friend")


def test_friend_cannot_resolve_operator_capability(monkeypatch):
    monkeypatch.setenv("MICHE_PROFILE", "friend")
    reg = load_registry(path=_FRIEND_REGISTRY)
    with pytest.raises(CapabilityError, match="caffenagent"):
        resolve_capability("caffenagent", "sessions", registry=reg)


def test_friend_home_hides_operator_chips(monkeypatch):
    monkeypatch.setenv("MICHE_PROFILE", "friend")
    reg = load_registry(path=_FRIEND_REGISTRY)

    class EmptySnap:
        items = []
        apps = []
        providers = []

    monkeypatch.setattr(
        "miche.routes.home._action_aggregator",
        MagicMock(collect=MagicMock(return_value=EmptySnap)),
    )
    monkeypatch.setattr(
        "miche.routes.home._info_aggregator",
        MagicMock(collect=MagicMock(return_value=EmptySnap)),
    )
    ctx = render_home(registry=reg)
    assert ctx["profile_id"] == "friend"
    assert ctx["app_chips"] == []


def test_router_audit_tags_profile_id(monkeypatch, tmp_path):
    log = tmp_path / "router.jsonl"
    monkeypatch.setenv("MICHE_ROUTER_FIXTURE", "cassette")
    monkeypatch.setenv("MICHE_ISLAND_ROUTER_FIXTURE", "cassette")
    monkeypatch.delenv("MICHE_PROFILE", raising=False)
    dispatch_utterance(
        utterance_id="u-tenancy",
        text="list sessions",
        audit_path=log,
    )
    row = json.loads(log.read_text().strip().splitlines()[-1])
    assert row["profile_id"] == active_profile_id()
    assert row["profile_id"] == "operator_default"


def test_friend_secrets_applied_without_operator_urls(monkeypatch, tmp_path):
    monkeypatch.setattr("miche.tenancy.profiles._PROFILE_ROOT", tmp_path)
    secrets_dir = tmp_path / "friend"
    secrets_dir.mkdir(parents=True)
    secrets_file = secrets_dir / "secrets.env"
    secrets_file.write_text("FRIEND_APP_PUBLIC_BASE_URL=https://friend.example.test\n")
    profile = load_install_profile("friend")
    profile.secrets_path = str(secrets_file)
    from miche.tenancy.profiles import apply_secrets

    monkeypatch.delenv("FRIEND_APP_PUBLIC_BASE_URL", raising=False)
    apply_secrets(profile)
    assert os.environ.get("FRIEND_APP_PUBLIC_BASE_URL") == "https://friend.example.test"


def test_friend_install_doc_never_commit_secrets():
    doc = (Path(__file__).resolve().parent.parent / "docs/friend_install.md").read_text().lower()
    assert "never commit" in doc
    assert "secrets" in doc


def test_active_profile_id_env_override(monkeypatch):
    monkeypatch.setenv("MICHE_PROFILE", "friend")
    assert active_profile_id() == "friend"
    monkeypatch.delenv("MICHE_PROFILE", raising=False)
    assert active_profile_id() == "operator_default"


def test_island_audit_tags_profile_id(monkeypatch, tmp_path):
    log = tmp_path / "island.jsonl"
    monkeypatch.setenv("MICHE_ROUTER_FIXTURE", "cassette")
    monkeypatch.setenv("MICHE_ISLAND_ROUTER_FIXTURE", "cassette")
    monkeypatch.delenv("MICHE_PROFILE", raising=False)
    route_utterance(utterance_id="u-island", text="list sessions", audit_path=log)
    row = json.loads(log.read_text().strip())
    assert row["profile_id"] == "operator_default"


def test_friend_dispatch_operator_app_rejected(monkeypatch):
    monkeypatch.setenv("MICHE_PROFILE", "friend")
    reg = load_registry(path=_FRIEND_REGISTRY)
    monkeypatch.setattr(
        "miche.router.dispatch.load_registry",
        lambda path=None, skip_profile=False: reg,
    )
    with pytest.raises(CapabilityError, match="caffenagent"):
        dispatch_utterance(
            utterance_id="u-friend-dispatch",
            text="ignored",
            force_app_id="caffenagent",
            force_capability="sessions",
        )


def test_friend_focus_operator_app_404(monkeypatch, client):
    monkeypatch.setenv("MICHE_PROFILE", "friend")
    monkeypatch.setattr(
        "miche.routes.focus.load_registry",
        lambda: load_registry(path=_FRIEND_REGISTRY),
    )
    r = client.get("/focus/caffenagent")
    assert r.status_code == 404


def test_friend_profile_clears_operator_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MICHE_PROFILE", "friend")
    monkeypatch.setenv("CAFFENAGENT_PUBLIC_BASE_URL", "https://operator.secret.test")
    monkeypatch.setattr("miche.tenancy.profiles._PROFILE_ROOT", tmp_path)
    secrets_dir = tmp_path / "friend"
    secrets_dir.mkdir(parents=True)
    profile = load_install_profile("friend")
    profile.secrets_path = str(secrets_dir / "secrets.env")
    monkeypatch.setattr("miche.tenancy.profiles.load_install_profile", lambda profile_id=None: profile)
    load_registry(path=_FRIEND_REGISTRY)
    assert os.environ.get("CAFFENAGENT_PUBLIC_BASE_URL") is None


def test_profile_yaml_id_must_match_filename(tmp_path, monkeypatch):
    bad = tmp_path / "friend.yaml"
    bad.write_text(
        "profile_id: wrong_id\napps: []\nsecrets_path: ~/.miche/profiles/friend/secrets.env\n"
    )
    monkeypatch.setattr("miche.tenancy.profiles._PROFILES_DIR", tmp_path)
    with pytest.raises(ProfileError, match="does not match file"):
        load_install_profile("friend")


def test_profile_apps_missing_from_registry_rejected(monkeypatch):
    monkeypatch.setenv("MICHE_PROFILE", "friend")
    raw = load_registry(path=_FRIEND_REGISTRY, skip_profile=True)
    profile = load_install_profile("friend")
    profile.apps = list(profile.apps) + ["nonexistent_app"]
    monkeypatch.setattr("miche.tenancy.profiles.load_install_profile", lambda profile_id=None: profile)
    with pytest.raises(ProfileError, match="not in registry"):
        apply_active_profile(raw)