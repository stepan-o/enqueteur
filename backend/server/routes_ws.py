from __future__ import annotations

"""WebSocket route shell for future live session binding."""

from typing import Any

from .models import ErrorBody


LIVE_WS_PATH = "/live"
WS_POLICY_VIOLATION = 1008
WS_TRY_AGAIN_LATER = 1013
LIVE_WS_PHASE_GATE = "S4"


def register_ws_routes(app: Any) -> None:
    """Attach websocket routes to the ASGI app."""

    # Import inside registration to keep module import-safe without framework deps.
    from fastapi import APIRouter, WebSocket

    router = APIRouter()

    @router.websocket(LIVE_WS_PATH)
    async def ws_live(websocket: WebSocket) -> None:
        run_id = websocket.query_params.get("run_id")
        await websocket.accept()

        if not run_id:
            payload = ErrorBody(
                code="MISSING_RUN_ID",
                message="run_id query parameter is required for /live.",
            )
            await websocket.send_json({"error": payload.to_dict()})
            await websocket.close(code=WS_POLICY_VIOLATION, reason="MISSING_RUN_ID")
            return

        payload = ErrorBody(
            code="NOT_IMPLEMENTED",
            message=(
                "Transport route exists, but live session protocol handling is not implemented in Phase S3. "
                "Phase S4 will attach real websocket lifecycle + protocol sequencing."
            ),
            details={"run_id": run_id, "phase_gate": LIVE_WS_PHASE_GATE},
        )
        await websocket.send_json({"error": payload.to_dict()})
        await websocket.close(code=WS_TRY_AGAIN_LATER, reason="NOT_IMPLEMENTED")

    app.include_router(router)


__all__ = [
    "register_ws_routes",
    "LIVE_WS_PATH",
    "LIVE_WS_PHASE_GATE",
    "WS_POLICY_VIOLATION",
    "WS_TRY_AGAIN_LATER",
]
