"""Platform apps API — MPLAT-SPR-01 read-only v0."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from ..health_probe import probe_app, probe_registry
from ..registry import AppRegistry, load_registry


def list_apps(*, registry: AppRegistry | None = None) -> dict[str, Any]:
    reg = registry or load_registry()
    return {"ok": True, **reg.as_public_dict()}


def get_app_health(app_id: str, *, registry: AppRegistry | None = None) -> dict[str, Any]:
    reg = registry or load_registry()
    app = reg.get(app_id)
    if app is None:
        raise HTTPException(status_code=404, detail=f"unknown app_id: {app_id}")
    result = probe_app(app, use_cache=False)
    return {"ok": True, "app_id": app_id, "health": result.as_dict()}


def register_routes(app) -> None:
    @app.get("/api/platform/apps")
    def platform_apps() -> JSONResponse:
        return JSONResponse(list_apps())

    @app.get("/api/platform/apps/{app_id}/health")
    def platform_app_health(app_id: str) -> JSONResponse:
        try:
            payload = get_app_health(app_id)
        except HTTPException:
            raise
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return JSONResponse(payload)