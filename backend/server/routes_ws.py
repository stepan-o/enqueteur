from __future__ import annotations

"""WebSocket route shell for future live session binding."""

from typing import Any

from .models import ErrorBody


WS_POLICY_VIOLATION = 1008
WS_TRY_AGAIN_LATER = 1013


def register_ws_routes(app: Any) -> None:
    """Attach websocket routes to the ASGI app."""

    # Import inside registration to keep module import-safe without framework deps.
    from fastapi import APIRouter, WebSocket

    router = APIRouter()

    @router.websocket("/live")
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
                "Transport route exists, but live session protocol handling is not implemented in Phase S1. "
                "Phase S4 will attach real websocket lifecycle + protocol sequencing."
            ),
            details={"run_id": run_id, "phase_gate": "S4"},
        )
        await websocket.send_json({"error": payload.to_dict()})
        await websocket.close(code=WS_TRY_AGAIN_LATER, reason="NOT_IMPLEMENTED")

    app.include_router(router)


__all__ = ["register_ws_routes", "WS_POLICY_VIOLATION", "WS_TRY_AGAIN_LATER"]
