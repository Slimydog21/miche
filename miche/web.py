"""Miche Platform FastAPI app — MPLAT-SPR-01."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .routes.apps import register_routes


def create_app() -> FastAPI:
    app = FastAPI(title="Miche Platform", version="0.1.0")

    @app.get("/api/health")
    def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "product": "miche_platform"})

    register_routes(app)
    return app


app = create_app()