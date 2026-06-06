"""Registry-backed capability map — MPLAT-SPR-06."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..registry import AppRegistry, CapabilityRegistration, load_registry


class CapabilityError(Exception):
    """Unknown or disabled app/capability."""

    def __init__(
        self,
        message: str,
        *,
        app_id: str | None = None,
        capability: str | None = None,
        allowed: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.app_id = app_id
        self.capability = capability
        self.allowed = allowed or []


@dataclass(frozen=True)
class ResolvedCapability:
    app_id: str
    capability: str
    invoke: str
    focus_route: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "capability": self.capability,
            "invoke": self.invoke,
            "focus_route": self.focus_route,
        }


def load_capability_map(*, registry: AppRegistry | None = None) -> dict[str, dict[str, ResolvedCapability]]:
    reg = registry or load_registry()
    out: dict[str, dict[str, ResolvedCapability]] = {}
    for app in reg.apps:
        if not app.enabled:
            continue
        caps: dict[str, ResolvedCapability] = {}
        for cap in app.capabilities:
            caps[cap.id] = ResolvedCapability(
                app_id=app.id,
                capability=cap.id,
                invoke=cap.invoke,
                focus_route=app.focus_route,
            )
        out[app.id] = caps
    return out


def allowed_capabilities(app_id: str, *, registry: AppRegistry | None = None) -> list[str]:
    reg = registry or load_registry()
    app = reg.get(app_id)
    if not app or not app.enabled:
        return []
    return [c.id for c in app.capabilities]


def resolve_capability(
    app_id: str,
    capability: str,
    *,
    registry: AppRegistry | None = None,
) -> ResolvedCapability:
    reg = registry or load_registry()
    app = reg.get(app_id)
    if not app or not app.enabled:
        raise CapabilityError(
            f"unknown or disabled app_id: {app_id}",
            app_id=app_id,
            capability=capability,
            allowed=[],
        )
    cap_map = {c.id: c for c in app.capabilities}
    if capability not in cap_map:
        raise CapabilityError(
            f"unknown capability '{capability}' for app '{app_id}'",
            app_id=app_id,
            capability=capability,
            allowed=sorted(cap_map.keys()),
        )
    raw: CapabilityRegistration = cap_map[capability]
    return ResolvedCapability(
        app_id=app_id,
        capability=capability,
        invoke=raw.invoke,
        focus_route=app.focus_route,
    )