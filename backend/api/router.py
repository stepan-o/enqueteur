from __future__ import annotations

"""Small framework-agnostic API router skeleton for backend HTTP integration."""

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .cases_start import (
    CASE_START_PATH,
    CaseStartService,
    get_default_case_start_service,
    handle_post_cases_start,
)


@dataclass(frozen=True)
class ApiRequest:
    method: str
    path: str
    json: Mapping[str, Any]


@dataclass(frozen=True)
class ApiResponse:
    status: int
    json: dict[str, Any]


RouteHandler = Callable[[Mapping[str, Any]], tuple[int, dict[str, Any]]]


class ApiRouter:
    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], RouteHandler] = {}

    def add(self, *, method: str, path: str, handler: RouteHandler) -> None:
        key = (method.upper(), path)
        self._routes[key] = handler

    def dispatch(self, req: ApiRequest) -> ApiResponse:
        key = (req.method.upper(), req.path)
        handler = self._routes.get(key)
        if handler is None:
            return ApiResponse(status=404, json={"error": {"code": "NOT_FOUND", "message": "Route not found."}})
        status, payload = handler(req.json)
        return ApiResponse(status=status, json=payload)


def build_default_router(*, case_start_service: CaseStartService | None = None) -> ApiRouter:
    service = case_start_service if case_start_service is not None else get_default_case_start_service()
    router = ApiRouter()
    router.add(
        method="POST",
        path=CASE_START_PATH,
        handler=lambda body: handle_post_cases_start(body, service=service),
    )
    return router


__all__ = [
    "ApiRequest",
    "ApiResponse",
    "RouteHandler",
    "ApiRouter",
    "build_default_router",
]
