"""Install profile loader — MPLAT-SPR-08."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from ..registry import AppRegistry

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
_PROFILES_DIR = _PACKAGE_ROOT / "interfaces" / "profiles"
_SCHEMA_PATH = _PACKAGE_ROOT / "schemas" / "miche_install_profile.json"
_PROFILE_ENV = "MICHE_PROFILE"
DEFAULT_PROFILE_ID = "operator_default"
_PROFILE_ROOT = Path.home() / ".miche" / "profiles"
_OPERATOR_CORPUS_MARKERS = ("/corpus/", "/operator-corpus/", "/operator/corpus/")


class ProfileError(Exception):
    """Install profile invariant violation."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        if path:
            message = f"{path}: {message}"
        super().__init__(message)
        self.path = path


@dataclass
class InstallProfile:
    profile_id: str
    apps: list[str]
    secrets_path: str
    source_path: str

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "apps": list(self.apps),
            "secrets_path": self.secrets_path,
        }


def active_profile_id() -> str:
    return os.environ.get(_PROFILE_ENV, "").strip() or DEFAULT_PROFILE_ID


def _load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


def _profile_path(profile_id: str) -> Path:
    return _PROFILES_DIR / f"{profile_id}.yaml"


def validate_secrets_path(raw: str, profile_id: str) -> Path:
    """Bound secrets_path to ~/.miche/profiles/<profile_id>/ — rigor §3."""
    if ".." in raw.split("/"):
        raise ProfileError("path traversal rejected in secrets_path")
    expanded = Path(raw).expanduser()
    if not expanded.is_absolute():
        expanded = (_PROFILE_ROOT / profile_id / expanded.name).resolve()
    else:
        expanded = expanded.resolve()

    allowed_root = (_PROFILE_ROOT / profile_id).resolve()
    try:
        expanded.relative_to(allowed_root)
    except ValueError as exc:
        raise ProfileError(
            f"secrets_path must stay under {allowed_root}",
            path=str(expanded),
        ) from exc

    lowered = str(expanded).lower()
    for marker in _OPERATOR_CORPUS_MARKERS:
        if marker in lowered:
            raise ProfileError("operator corpus paths forbidden for tenant installs", path=str(expanded))
    return expanded


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key:
            values[key] = val
    return values


def apply_secrets(profile: InstallProfile) -> None:
    """Load tenant secrets from profile-bound path; skip quietly if file absent."""
    path = validate_secrets_path(profile.secrets_path, profile.profile_id)
    if not path.is_file():
        return
    for key, val in _parse_dotenv(path).items():
        os.environ.setdefault(key, val)


def load_install_profile(profile_id: str | None = None) -> InstallProfile:
    pid = profile_id or active_profile_id()
    path = _profile_path(pid)
    if not path.is_file():
        raise ProfileError(f"install profile not found: {pid}", path=str(path))

    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ProfileError("profile root must be a mapping", path=str(path))

    schema = _load_schema()
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ProfileError(str(exc.message), path=exc.json_path or str(path)) from exc

    return InstallProfile(
        profile_id=str(data["profile_id"]),
        apps=[str(a) for a in data.get("apps") or []],
        secrets_path=str(data["secrets_path"]),
        source_path=str(path),
    )


def apply_active_profile(registry: AppRegistry) -> AppRegistry:
    """Overlay registry with active install profile; hard-fail on mix-up."""
    profile = load_install_profile(active_profile_id())
    if profile.profile_id != registry.install_profile:
        raise ProfileError(
            f"profile mix-up: active profile {profile.profile_id!r} "
            f"does not match registry install_profile {registry.install_profile!r}"
        )

    apply_secrets(profile)

    registry_ids = {a.id for a in registry.apps}
    unknown = set(profile.apps) - registry_ids
    if unknown:
        raise ProfileError(f"profile apps not in registry: {sorted(unknown)}")

    allowed = set(profile.apps)
    filtered = [a for a in registry.apps if a.id in allowed]
    return AppRegistry(
        version=registry.version,
        install_profile=profile.profile_id,
        apps=filtered,
        source_path=registry.source_path,
    )