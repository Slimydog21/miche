"""caffenagent API proxy — MPLAT-ORCH-SPR-01.

Thin reverse proxy that forwards Miche browser requests to the caffenagent
server, handling auth and CORS transparently. The browser hits
/api/caffenagent/* and never sees caffenagent's actual host/port/credentials.

Why this exists: caffenagent runs on a separate port with HTTPBasic auth.
Exposing raw caffenagent URLs to the browser would require CORS headers on
caffenagent and credential management in JS. The proxy centralizes both.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from ..registry import load_registry

_TIMEOUT = 10.0
_MAX_BODY_BYTES = 10 * 1024 * 1024  # 10MB — prevent OOM from oversized uploads


def _resolve_base_url() -> str | None:
    """Read caffenagent's base URL from the app registry's base_url_env."""
    reg = load_registry()
    app = reg.get("caffenagent")
    if app is None or not app.enabled:
        return None
    return app.resolve_base_url()


def _build_auth_headers() -> dict[str, str]:
    """Build Basic auth header from env vars (server-side only, never exposed to browser).

    Returns empty dict if credentials are not configured — callers should
    check and return 503 rather than forward unauthenticated.
    """
    user = os.environ.get("CAFFENAGENT_WEB_USER", "").strip()
    pw = os.environ.get("CAFFENAGENT_WEB_PASS", "").strip()
    if not user or not pw:
        return {}
    import base64

    creds = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return {"Authorization": f"Basic {creds}"}


def register_routes(app) -> None:
    @app.api_route(
        "/api/caffenagent/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    async def proxy_to_caffenagent(path: str, request: Request) -> Response:
        """Forward requests to caffenagent, handling auth transparently."""
        base = _resolve_base_url()
        if not base:
            return JSONResponse(
                {
                    "ok": False,
                    "code": "caffenagent_unreachable",
                    "message": "CAFFENAGENT_PUBLIC_BASE_URL is not configured. Set it in the app registry or environment.",
                },
                status_code=503,
            )

        target = f"{base.rstrip('/')}/{path}"
        if request.url.query:
            target = f"{target}?{request.url.query}"

        headers = _build_auth_headers()
        if not headers:
            return JSONResponse(
                {
                    "ok": False,
                    "code": "auth_env_unset",
                    "message": "CAFFENAGENT_WEB_USER / CAFFENAGENT_WEB_PASS not configured. Set these in .env before proxying.",
                },
                status_code=503,
            )
        # Forward content-type but not host/auth from the original request
        ct = request.headers.get("content-type")
        if ct:
            headers["content-type"] = ct

        body = None
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            if len(body) > _MAX_BODY_BYTES:
                return JSONResponse(
                    {"ok": False, "code": "payload_too_large", "message": "Request body exceeds 10MB limit."},
                    status_code=413,
                )

        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client:
            try:
                r = await client.request(
                    method=request.method,
                    url=target,
                    headers=headers,
                    content=body,
                )
            except httpx.HTTPError:
                return JSONResponse(
                    {
                        "ok": False,
                        "code": "proxy_error",
                        "message": "Failed to reach caffenagent — check that the server is running and CAFFENAGENT_PUBLIC_BASE_URL is correct.",
                    },
                    status_code=502,
                )

        # Forward caffenagent's response verbatim (status + body + content-type)
        resp_headers = {}
        ct_resp = r.headers.get("content-type")
        if ct_resp:
            resp_headers["content-type"] = ct_resp

        return Response(
            content=r.content,
            status_code=r.status_code,
            headers=resp_headers,
        )
