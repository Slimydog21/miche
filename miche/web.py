"""Miche Platform FastAPI app — MPLAT-SPR-01 + home shell."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .routes.apps import register_routes as register_apps_routes
from .routes.home import register_routes as register_home_routes
from .routes.inbox import register_routes as register_inbox_routes
from .routes.island import register_routes as register_island_routes
from .routes.focus import register_routes as register_focus_routes
from .routes.router import register_routes as register_router_routes
from .routes.persona import register_routes as register_persona_routes
from .registry import load_registry

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    load_registry()
    app = FastAPI(title="Miche Platform", version="0.1.0")

    @app.get("/api/health")
    def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "product": "miche_platform"})

    register_apps_routes(app)
    register_inbox_routes(app)
    register_island_routes(app)
    register_router_routes(app)
    register_persona_routes(app)
    register_focus_routes(app)
    register_home_routes(app)
    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    return app


app = create_app()