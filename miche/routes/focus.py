"""Focus mode bridge routes — MPLAT-SPR-07."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..focus.handoff import create_handoff, restore_payload
from ..registry import RegistryError, load_registry

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def register_routes(app) -> None:
    @app.get("/focus/{app_id}", response_class=HTMLResponse)
    def focus_shell(
        request: Request,
        app_id: str,
        path: str | None = None,
        island_expanded: bool = False,
        utterance_id: str | None = None,
        router_decision_id: str | None = None,
    ) -> HTMLResponse:
        reg = load_registry()
        app_reg = reg.get(app_id)
        if not app_reg or not app_reg.enabled:
            raise HTTPException(status_code=404, detail="app not found")

        focus_path = path or app_reg.focus_route or "/"
        try:
            handoff = create_handoff(
                app_id=app_id,
                path=focus_path,
                island_expanded=island_expanded,
                utterance_id=utterance_id,
                router_decision_id=router_decision_id,
            )
        except (RegistryError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if handoff["embed_mode"] == "navigate" and handoff.get("target_url"):
            target = handoff["target_url"]
            sep = "&" if "?" in target else "?"
            return RedirectResponse(
                url=f"{target}{sep}miche_handoff={handoff['handoff_id']}",
                status_code=302,
            )

        return templates.TemplateResponse(
            request,
            "focus.html",
            {
                "request": request,
                "app_id": app_id,
                "display_name": app_reg.display_name,
                "handoff": handoff,
                "home_return_url": f"/?focus_return={handoff['handoff_id']}",
            },
        )

    @app.get("/api/platform/focus/restore")
    def focus_restore(handoff_id: str) -> JSONResponse:
        payload = restore_payload(handoff_id)
        if not payload:
            raise HTTPException(status_code=404, detail="handoff expired or not found")
        return JSONResponse(payload)