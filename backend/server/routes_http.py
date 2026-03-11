from __future__ import annotations

"""HTTP route shell for transport lifecycle endpoints."""

from datetime import UTC, datetime
from typing import Any

from .models import ErrorBody, PlaceholderCaseStartResponse, ServerHealthResponse


def register_http_routes(app: Any) -> None:
    """Attach HTTP routes to the ASGI app."""

    # Import inside registration to keep module import-safe without framework deps.
    from fastapi import APIRouter, Request
    from fastapi.responses import JSONResponse

    router = APIRouter()
    started_at = datetime.now(UTC).isoformat()

    @router.get("/healthz")
    async def healthz() -> dict[str, str]:
        payload = ServerHealthResponse(
            status="ok",
            service="enqueteur-server-shell",
            started_at=started_at,
        )
        return payload.to_dict()

    @router.get("/readyz")
    async def readyz(request: Request) -> dict[str, str]:
        started = bool(getattr(request.app.state, "started", False))
        status = "ready" if started else "starting"
        payload = ServerHealthResponse(
            status=status,
            service="enqueteur-server-shell",
            started_at=started_at,
        )
        return payload.to_dict()

    @router.post("/api/cases/start")
    async def post_cases_start() -> JSONResponse:
        body = ErrorBody(
            code="NOT_IMPLEMENTED",
            message=(
                "Transport route exists, but case launch wiring is not implemented in Phase S1. "
                "Phase S2 will connect this endpoint to launch orchestration."
            ),
        )
        payload = {
            "error": body.to_dict(),
            "phase_gate": "S2",
            "placeholder": PlaceholderCaseStartResponse().to_dict(),
        }
        return JSONResponse(status_code=501, content=payload)

    app.include_router(router)


__all__ = ["register_http_routes"]
