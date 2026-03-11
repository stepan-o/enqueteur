from __future__ import annotations

"""HTTP route shell for transport lifecycle endpoints."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from backend.api.cases_start import CaseStartService, handle_post_cases_start

from .config import ServerConfig
from .models import CaseStartTransportRequest, ServerHealthResponse
from .run_registry import RunRegistry
from .routes_ws import LIVE_WS_PATH

HEALTH_PATH = "/healthz"
READINESS_PATH = "/readyz"
CASE_START_PATH = "/api/cases/start"
CASE_START_PHASE_GATE = "S2"
HOST_NOT_READY_CODE = "HOST_NOT_READY"


def build_ws_base_url(config: ServerConfig) -> str:
    host = config.host.strip() or "127.0.0.1"
    if host in {"0.0.0.0", "::"}:
        host = "localhost"
    return f"ws://{host}:{config.port}{LIVE_WS_PATH}"


def launch_case_from_transport(
    payload: CaseStartTransportRequest,
    *,
    case_start_service: CaseStartService,
    run_registry: RunRegistry,
) -> tuple[int, dict[str, Any]]:
    status, response_payload = handle_post_cases_start(payload.to_core_payload(), service=case_start_service)

    if status == 200:
        run_id = response_payload.get("run_id")
        started_run = (
            case_start_service.registry.get(run_id)
            if isinstance(run_id, str) and run_id
            else None
        )
        run_registry.register_launched_run(
            launch_payload=response_payload,
            started_run=started_run,
        )

    return status, response_payload


def _host_not_ready_response(message: str) -> dict[str, Any]:
    return {
        "error": {
            "code": HOST_NOT_READY_CODE,
            "message": message,
        },
        "phase_gate": CASE_START_PHASE_GATE,
    }


def register_http_routes(app: Any) -> None:
    """Attach HTTP routes to the ASGI app."""

    # Import inside registration to keep module import-safe without framework deps.
    from fastapi import APIRouter, Request
    from fastapi.responses import JSONResponse

    router = APIRouter()
    started_at = datetime.now(UTC).isoformat()

    @router.get(HEALTH_PATH)
    async def healthz() -> dict[str, str]:
        payload = ServerHealthResponse(
            status="ok",
            service="enqueteur-server-shell",
            started_at=started_at,
        )
        return payload.to_dict()

    @router.get(READINESS_PATH)
    async def readyz(request: Request) -> dict[str, str]:
        started = bool(getattr(request.app.state, "started", False))
        status = "ready" if started else "starting"
        payload = ServerHealthResponse(
            status=status,
            service="enqueteur-server-shell",
            started_at=started_at,
        )
        return payload.to_dict()

    @router.post(CASE_START_PATH)
    async def post_cases_start(request: Request) -> JSONResponse:
        try:
            raw_payload = await request.json()
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "INVALID_REQUEST",
                        "field": "payload",
                        "message": "Request body must be valid JSON.",
                    }
                },
            )

        if not isinstance(raw_payload, Mapping):
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "INVALID_REQUEST",
                        "field": "payload",
                        "message": "Request body must be a JSON object.",
                    }
                },
            )

        transport_request = CaseStartTransportRequest.from_payload(raw_payload)

        case_start_service = getattr(request.app.state, "case_start_service", None)
        run_registry = getattr(request.app.state, "run_registry", None)
        if not isinstance(case_start_service, CaseStartService):
            payload = _host_not_ready_response("Case start service is not initialized.")
            return JSONResponse(status_code=503, content=payload)
        if not isinstance(run_registry, RunRegistry):
            payload = _host_not_ready_response("Run registry is not initialized.")
            return JSONResponse(status_code=503, content=payload)

        status, payload = launch_case_from_transport(
            transport_request,
            case_start_service=case_start_service,
            run_registry=run_registry,
        )

        return JSONResponse(status_code=status, content=payload)

    app.include_router(router)


__all__ = [
    "register_http_routes",
    "HEALTH_PATH",
    "READINESS_PATH",
    "CASE_START_PATH",
    "CASE_START_PHASE_GATE",
    "HOST_NOT_READY_CODE",
    "build_ws_base_url",
    "launch_case_from_transport",
]
