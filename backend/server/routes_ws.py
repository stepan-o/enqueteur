from __future__ import annotations

"""WebSocket route wiring for live session controller."""

from typing import Any

from .models import ErrorBody
from .session_controller import (
    MISSING_RUN_ID_WS_CLOSE_CODE,
    POST_BASELINE_NOT_IMPLEMENTED_WS_CLOSE_CODE,
    SessionController,
)


LIVE_WS_PATH = "/live"
WS_POLICY_VIOLATION = MISSING_RUN_ID_WS_CLOSE_CODE
WS_TRY_AGAIN_LATER = POST_BASELINE_NOT_IMPLEMENTED_WS_CLOSE_CODE
WS_INTERNAL_ERROR = 1011
LIVE_WS_PHASE_GATE = "S4"


def register_ws_routes(app: Any) -> None:
    """Attach websocket routes to the ASGI app."""

    # Import inside registration to keep module import-safe without framework deps.
    from fastapi import APIRouter, WebSocket

    router = APIRouter()

    @router.websocket(LIVE_WS_PATH)
    async def ws_live(websocket: WebSocket) -> None:
        session_controller = getattr(websocket.app.state, "session_controller", None)
        if not isinstance(session_controller, SessionController):
            await websocket.accept()
            payload = ErrorBody(
                code="HOST_NOT_READY",
                message="Session controller is not initialized for /live.",
            )
            await websocket.send_json({"error": payload.to_dict()})
            await websocket.close(code=WS_INTERNAL_ERROR, reason="HOST_NOT_READY")
            return

        await session_controller.serve_live_handshake_baseline(
            websocket=websocket,
            connection_target=str(websocket.url),
        )

    app.include_router(router)


__all__ = [
    "register_ws_routes",
    "LIVE_WS_PATH",
    "LIVE_WS_PHASE_GATE",
    "WS_POLICY_VIOLATION",
    "WS_TRY_AGAIN_LATER",
    "WS_INTERNAL_ERROR",
]
