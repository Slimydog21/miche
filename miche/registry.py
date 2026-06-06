"""Miche app registry loader — MPLAT-SPR-01."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = _PACKAGE_ROOT / "interfaces" / "miche_app_registry.yaml"
SCHEMA_PATH = _PACKAGE_ROOT / "interfaces" / "schemas" / "miche_app_registry.schema.json"

_SECRET_ENV_SUFFIXES = ("_SECRET", "_TOKEN", "_KEY", "_PASSWORD")


class RegistryError(Exception):
    """Registry invariant violation."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        if path:
            message = f"{path}: {message}"
        super().__init__(message)
        self.path = path


@dataclass
class CapabilityRegistration:
    id: str
    invoke: str

    def as_public_dict(self) -> dict[str, str]:
        return {"id": self.id, "invoke": self.invoke}


@dataclass
class AppRegistration:
    id: str
    display_name: str
    repo: str | None = None
    enabled: bool = True
    base_url_env: str | None = None
    health_path: str = "/api/health"
    capabilities: list[CapabilityRegistration] = field(default_factory=list)
    focus_route: str | None = None
    action_webhook_env: str | None = None
    information_webhook_env: str | None = None

    def resolve_base_url(self) -> str | None:
        if not self.base_url_env:
            return None
        return (os.environ.get(self.base_url_env) or "").strip() or None

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "repo": self.repo,
            "enabled": self.enabled,
            "health_path": self.health_path,
            "capabilities": [c.as_public_dict() for c in self.capabilities],
            "focus_route": self.focus_route,
            "base_url_configured": bool(self.resolve_base_url()),
        }


@dataclass
class AppRegistry:
    version: str
    install_profile: str
    apps: list[AppRegistration]
    source_path: str

    def get(self, app_id: str) -> AppRegistration | None:
        return next((a for a in self.apps if a.id == app_id), None)

    def enabled_apps(self) -> list[AppRegistration]:
        return [a for a in self.apps if a.enabled]

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "install_profile": self.install_profile,
            "apps": [a.as_public_dict() for a in self.apps],
        }


def _validate_semantics(data: dict[str, Any], *, source: str) -> None:
    seen: set[str] = set()
    for idx, raw in enumerate(data.get("apps") or []):
        app_id = str(raw.get("id") or "")
        path = f"apps[{idx}].id"
        if app_id in seen:
            raise RegistryError(f"duplicate id {app_id!r}", path=path)
        seen.add(app_id)

        enabled = bool(raw.get("enabled", True))
        base_env = raw.get("base_url_env")
        if enabled and not base_env:
            raise RegistryError("enabled app requires base_url_env", path=f"apps[{idx}].base_url_env")

        focus = raw.get("focus_route")
        if focus is not None and not str(focus).startswith("/"):
            raise RegistryError("focus_route must start with /", path=f"apps[{idx}].focus_route")

        for cidx, cap in enumerate(raw.get("capabilities") or []):
            if isinstance(cap, str):
                raise RegistryError("capability must be object with invoke", path=f"apps[{idx}].capabilities[{cidx}]")
            if not cap.get("invoke"):
                raise RegistryError("capability missing invoke", path=f"apps[{idx}].capabilities[{cidx}].invoke")


def _parse_capability(raw: Any) -> CapabilityRegistration:
    if isinstance(raw, str):
        raise RegistryError("capability shorthand not allowed — use id + invoke")
    return CapabilityRegistration(id=str(raw["id"]), invoke=str(raw["invoke"]))


def _parse_app(raw: dict[str, Any]) -> AppRegistration:
    caps = [_parse_capability(c) for c in raw.get("capabilities") or []]
    return AppRegistration(
        id=str(raw["id"]),
        display_name=str(raw["display_name"]),
        repo=raw.get("repo"),
        enabled=bool(raw.get("enabled", True)),
        base_url_env=raw.get("base_url_env"),
        health_path=str(raw.get("health_path") or "/api/health"),
        capabilities=caps,
        focus_route=raw.get("focus_route"),
        action_webhook_env=raw.get("action_webhook_env"),
        information_webhook_env=raw.get("information_webhook_env"),
    )


def load_registry(path: Path | None = None) -> AppRegistry:
    """Load and validate registry YAML."""
    reg_path = path or DEFAULT_REGISTRY_PATH
    if not reg_path.is_file():
        raise RegistryError(f"registry not found: {reg_path}")

    data = yaml.safe_load(reg_path.read_text())
    if not isinstance(data, dict):
        raise RegistryError("registry root must be a mapping", path=str(reg_path))

    schema = json.loads(SCHEMA_PATH.read_text())
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise RegistryError(str(exc.message), path=exc.json_path or str(reg_path)) from exc

    _validate_semantics(data, source=str(reg_path))
    apps = [_parse_app(a) for a in data.get("apps") or []]
    return AppRegistry(
        version=str(data.get("version") or ""),
        install_profile=str(data.get("install_profile") or "default"),
        apps=apps,
        source_path=str(reg_path),
    )


def redact_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip env secret field names from API responses."""
    return {k: v for k, v in payload.items() if not any(k.endswith(s) for s in _SECRET_ENV_SUFFIXES)}