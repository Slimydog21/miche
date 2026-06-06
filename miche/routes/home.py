"""Home page shell — MPLAT-SPR-02."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..registry import AppRegistry, RegistryError, load_registry

_LAYOUT_VERSION = "1"
MOUNT_ELEMENT_ID = "miche-island-mount"
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _chip_apps(registry: AppRegistry) -> list[dict[str, Any]]:
    chips: list[dict[str, Any]] = []
    for app in registry.apps:
        if not app.enabled or not app.focus_route:
            continue
        chips.append(
            {
                "id": app.id,
                "display_name": app.display_name,
                "focus_route": app.focus_route,
                "href": f"/focus/{app.id}",
            }
        )
    return chips


def render_home(*, registry: AppRegistry | None = None) -> dict[str, Any]:
    registry_error: str | None = None
    reg = registry
    if reg is None:
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

    return {
        "layout_version": _LAYOUT_VERSION,
        "install_profile": reg.install_profile,
        "app_chips": _chip_apps(reg),
        "registry_error": registry_error,
    }


def register_routes(app) -> None:
    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        ctx = render_home()
        status_code = 200 if ctx["registry_error"] is None else 503
        return templates.TemplateResponse(
            request,
            "home.html",
            {
                "request": request,
                **ctx,
            },
            status_code=status_code,
        )