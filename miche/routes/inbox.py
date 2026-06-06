"""Platform inbox API — MPLAT-SPR-03 + information MPLAT-SPR-04."""

from __future__ import annotations

from fastapi.responses import JSONResponse

from ..adapters.caffenagent_actions import make_fetcher
from ..adapters.caffenagent_information import make_gap_fetcher
from ..inbox.action import ActionInboxAggregator
from ..inbox.information import AuditProvider, DeployProvider, GapProvider, InformationInboxAggregator

_action_aggregator = ActionInboxAggregator(fetcher=make_fetcher())
_info_aggregator = InformationInboxAggregator(
    providers=[
        GapProvider(fetch_gap_items=make_gap_fetcher()),
        DeployProvider(),
        AuditProvider(),
    ]
)


def get_action_inbox(*, force: bool = False) -> dict:
    return _action_aggregator.collect(force=force).as_dict()


def get_information_inbox(*, force: bool = False) -> dict:
    return _info_aggregator.collect(force=force).as_dict()


def register_routes(app) -> None:
    @app.get("/api/platform/inbox/actions")
    def platform_action_inbox(force: bool = False) -> JSONResponse:
        return JSONResponse(get_action_inbox(force=force))

    @app.get("/api/platform/inbox/information")
    def platform_information_inbox(force: bool = False) -> JSONResponse:
        return JSONResponse(get_information_inbox(force=force))