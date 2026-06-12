"""Gap analysis dashboard route — MPLAT-ORCH batch 4."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def register_routes(app) -> None:
    @app.get("/orchestrate/gaps", response_class=HTMLResponse)
    def gap_dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "gaps.html",
            {"request": request},
        )
