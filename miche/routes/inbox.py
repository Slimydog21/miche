"""Platform inbox API — MPLAT-SPR-03."""

from __future__ import annotations

from fastapi.responses import JSONResponse

from ..adapters.caffenagent_actions import make_fetcher
from ..inbox.action import ActionInboxAggregator

_aggregator = ActionInboxAggregator(fetcher=make_fetcher())


def get_action_inbox(*, force: bool = False) -> dict:
    return _aggregator.collect(force=force).as_dict()


def register_routes(app) -> None:
    @app.get("/api/platform/inbox/actions")
    def platform_action_inbox(force: bool = False) -> JSONResponse:
        return JSONResponse(get_action_inbox(force=force))