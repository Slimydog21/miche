"""Orchestration dashboard route — MPLAT-ORCH-SPR-02."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..registry import RegistryError, load_registry
from ..tenancy.profiles import active_profile_id

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _chip_apps(registry, *, profile_id: str) -> list[dict[str, Any]]:
    from .home import _chip_apps as home_chip_apps

    return home_chip_apps(registry, profile_id=profile_id)


def register_routes(app) -> None:
    @app.get("/orchestrate", response_class=HTMLResponse)
    def orchestrate(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "orchestrate.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )

    @app.get("/orchestrate/pr-queue", response_class=HTMLResponse)
    def pr_queue(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "pr_queue.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )

    @app.get("/orchestrate/graph", response_class=HTMLResponse)
    def graph(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "graph.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )

    @app.get("/orchestrate/specs", response_class=HTMLResponse)
    def specs(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "specs.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )

    @app.get("/orchestrate/studio", response_class=HTMLResponse)
    def studio(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "studio.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )

    @app.get("/orchestrate/settings", response_class=HTMLResponse)
    def settings(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "settings.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )

    @app.get("/orchestrate/voice", response_class=HTMLResponse)
    def voice(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "voice.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )

    @app.get("/orchestrate/memory", response_class=HTMLResponse)
    def memory(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "memory.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )

    @app.get("/orchestrate/connectors", response_class=HTMLResponse)
    def connectors(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "connectors.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )

    @app.get("/orchestrate/workstation", response_class=HTMLResponse)
    def workstation(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "workstation.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )

    @app.get("/orchestrate/metrics", response_class=HTMLResponse)
    def metrics(request: Request) -> HTMLResponse:
        registry_error = None
        try:
            reg = load_registry()
        except RegistryError as exc:
            registry_error = str(exc)
            from ..registry import AppRegistry

            reg = AppRegistry(version="0", install_profile="degraded", apps=[], source_path="")

        pid = active_profile_id()
        return templates.TemplateResponse(
            request,
            "metrics.html",
            {
                "request": request,
                "layout_version": "1",
                "install_profile": reg.install_profile,
                "profile_id": pid,
                "app_chips": _chip_apps(reg, profile_id=pid),
                "registry_error": registry_error,
            },
        )
