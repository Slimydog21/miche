"""Miche persona API — MPLAT-SPR-09."""

from __future__ import annotations

from fastapi import HTTPException, Query
from fastapi.responses import JSONResponse

from ..mascot.assets import AssetError
from ..mascot.persona import resolve_persona


def register_routes(app) -> None:
    @app.get("/api/miche/persona")
    def miche_persona(
        context: str = Query(..., description="home or island"),
        reduced_motion: bool = Query(False),
    ) -> JSONResponse:
        try:
            payload = resolve_persona(context=context, reduced_motion=reduced_motion)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except AssetError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return JSONResponse(payload)