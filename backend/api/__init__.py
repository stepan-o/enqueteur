"""Backend API surface for Enqueteur playability flows."""

from .cases_start import (
    CASE_START_PATH,
    ENQUETEUR_ENGINE_NAME,
    ENQUETEUR_SCHEMA_VERSION,
    CaseStartRequest,
    CaseStartResponse,
    CaseStartService,
    StartCaseMode,
)
from .live_ws import (
    ENQUETEUR_LIVE_WS_PATH,
    RUN_NOT_FOUND_WS_CLOSE_CODE,
    RUN_NOT_FOUND_WS_CLOSE_REASON,
    EnqueteurLiveSession,
    EnqueteurLiveSessionHost,
    RunLookupError,
    get_default_enqueteur_live_session_host,
    open_enqueteur_live_websocket,
)
from .router import ApiRequest, ApiResponse, build_default_router

__all__ = [
    "ApiRequest",
    "ApiResponse",
    "CASE_START_PATH",
    "ENQUETEUR_LIVE_WS_PATH",
    "ENQUETEUR_ENGINE_NAME",
    "ENQUETEUR_SCHEMA_VERSION",
    "RUN_NOT_FOUND_WS_CLOSE_CODE",
    "RUN_NOT_FOUND_WS_CLOSE_REASON",
    "CaseStartRequest",
    "CaseStartResponse",
    "CaseStartService",
    "EnqueteurLiveSession",
    "EnqueteurLiveSessionHost",
    "RunLookupError",
    "StartCaseMode",
    "build_default_router",
    "get_default_enqueteur_live_session_host",
    "open_enqueteur_live_websocket",
]
