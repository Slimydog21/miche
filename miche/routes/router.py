"""Intent router HTTP API — MPLAT-SPR-06."""

from __future__ import annotations

from typing import Any

from fastapi import Body, HTTPException
from fastapi.responses import JSONResponse

from ..router.capability_map import CapabilityError, resolve_capability
from ..router.dispatch import dispatch_utterance, dispatch_mode


def post_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    utterance_id = str(body.get("utterance_id") or "").strip()
    text = str(body.get("text") or "").strip()
    if not utterance_id:
        raise HTTPException(status_code=400, detail="utterance_id required")
    if not text:
        raise HTTPException(status_code=400, detail="text required")

    force_app = body.get("app_id")
    force_cap = body.get("capability")
    try:
        if force_app and force_cap:
            resolve_capability(str(force_app), str(force_cap))
        return {
            "ok": True,
            **dispatch_utterance(
                utterance_id=utterance_id,
                text=text,
                source=str(body.get("source") or "api"),
                force_app_id=str(force_app) if force_app else None,
                force_capability=str(force_cap) if force_cap else None,
            ),
        }
    except CapabilityError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": str(exc),
                "app_id": exc.app_id,
                "capability": exc.capability,
                "allowed_capabilities": exc.allowed,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def register_routes(app) -> None:
    @app.post("/api/miche/router/dispatch")
    async def router_dispatch(request_body: dict = Body(...)) -> JSONResponse:
        payload = post_dispatch(request_body)
        return JSONResponse(payload)

    @app.get("/api/miche/router/mode")
    def router_mode_endpoint() -> JSONResponse:
        return JSONResponse({"ok": True, "mode": dispatch_mode()})