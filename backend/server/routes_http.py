"""HTTP route shell for transport lifecycle endpoints."""

from collections.abc import Mapping
from datetime import UTC, datetime
import logging
from typing import Any

from backend.api.cases_start import CaseStartService, handle_post_cases_start

from .config import ServerConfig
from .errors import (
    HostNotReadyError,
    LaunchContractError,
    LaunchExecutionError,
    TransportRequestError,
    TransportRouteError,
)
from .models import CaseStartTransportRequest, ServerHealthResponse
from .run_registry import RunRegistry
from .routes_ws import LIVE_WS_PATH

HEALTH_PATH = "/healthz"
READINESS_PATH = "/readyz"
CASE_START_PATH = "/api/cases/start"
CASE_START_PHASE_GATE = "S2"
HOST_NOT_READY_CODE = "HOST_NOT_READY"
logger = logging.getLogger(__name__)


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
    logger.info(
        "launch request case_id=%s mode=%s difficulty_profile=%s",
        payload.case_id,
        payload.mode,
        payload.difficulty_profile,
    )
    try:
        status, response_payload = handle_post_cases_start(payload.to_core_payload(), service=case_start_service)
    except Exception as exc:  # pragma: no cover - safety boundary for unexpected core errors.
        logger.exception("launch failed category=execution case_id=%s", payload.case_id)
        raise LaunchExecutionError() from exc

    if not isinstance(status, int):
        logger.error("launch failed category=contract reason=invalid_status type=%s", type(status).__name__)
        raise LaunchContractError("Case launch backend returned an invalid HTTP status value.")
    if not isinstance(response_payload, dict):
        logger.error("launch failed category=contract reason=invalid_payload type=%s", type(response_payload).__name__)
        raise LaunchContractError("Case launch backend returned a non-object response payload.")

    if status == 200:
        started_run = None
        run_id_candidate = response_payload.get("run_id")
        if isinstance(run_id_candidate, str) and run_id_candidate:
            started_run = case_start_service.registry.get(run_id_candidate)
        try:
            run_registry.register_launched_run(
                launch_payload=response_payload,
                started_run=started_run,
            )
        except Exception as exc:  # pragma: no cover - defensive mapping boundary.
            logger.exception("launch failed category=contract reason=registry_registration run_id=%s", run_id_candidate)
            raise LaunchContractError(
                "Case launch metadata could not be registered for future live attachment."
            ) from exc
        logger.info("launch success run_id=%s case_id=%s", run_id_candidate, payload.case_id)
    else:
        error_block = response_payload.get("error")
        error_code = error_block.get("code") if isinstance(error_block, dict) else None
        error_field = error_block.get("field") if isinstance(error_block, dict) else None
        logger.info(
            "launch rejected category=validation status=%s code=%s field=%s",
            status,
            error_code,
            error_field,
        )

    return status, response_payload


def parse_case_start_transport_request(raw_payload: object) -> CaseStartTransportRequest:
    if not isinstance(raw_payload, Mapping):
        raise TransportRequestError("Request body must be a JSON object.")
    return CaseStartTransportRequest.from_payload(raw_payload)


def resolve_launch_dependencies(app: Any) -> tuple[CaseStartService, RunRegistry]:
    case_start_service = getattr(app.state, "case_start_service", None)
    run_registry = getattr(app.state, "run_registry", None)
    if not isinstance(case_start_service, CaseStartService):
        raise HostNotReadyError("Case start service is not initialized.", phase_gate=CASE_START_PHASE_GATE)
    if not isinstance(run_registry, RunRegistry):
        raise HostNotReadyError("Run registry is not initialized.", phase_gate=CASE_START_PHASE_GATE)
    return case_start_service, run_registry


def build_transport_error_payload(error: TransportRouteError) -> dict[str, Any]:
    content: dict[str, Any] = {
        "error": {
            "code": error.code,
            "message": str(error),
        }
    }
    if error.field is not None:
        content["error"]["field"] = error.field
    if error.phase_gate is not None:
        content["phase_gate"] = error.phase_gate
    return content


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
        shutting_down = bool(getattr(request.app.state, "shutting_down", False))
        if shutting_down:
            status = "stopping"
        else:
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
            error = TransportRequestError("Request body must be valid JSON.")
            logger.warning("launch request rejected category=malformed_json")
            return JSONResponse(status_code=error.status_code, content=build_transport_error_payload(error))

        try:
            transport_request = parse_case_start_transport_request(raw_payload)
            case_start_service, run_registry = resolve_launch_dependencies(request.app)
            status, payload = launch_case_from_transport(
                transport_request,
                case_start_service=case_start_service,
                run_registry=run_registry,
            )
        except TransportRouteError as error:
            level = logging.ERROR if error.status_code >= 500 else logging.WARNING
            logger.log(
                level,
                "launch route error category=%s status=%s code=%s field=%s phase_gate=%s",
                error.__class__.__name__,
                error.status_code,
                error.code,
                error.field,
                error.phase_gate,
            )
            return JSONResponse(status_code=error.status_code, content=build_transport_error_payload(error))
        except Exception:  # pragma: no cover - defensive transport boundary
            error = LaunchExecutionError()
            logger.exception("launch route internal_error category=unexpected")
            return JSONResponse(status_code=error.status_code, content=build_transport_error_payload(error))

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
    "build_transport_error_payload",
    "launch_case_from_transport",
    "parse_case_start_transport_request",
    "resolve_launch_dependencies",
]
