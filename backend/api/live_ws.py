from __future__ import annotations

"""Enqueteur LIVE WebSocket entrypoint and run-attachment host.

Phase D1 scope:
- attach incoming websocket connections to already-created runs
- maintain per-connection protocol phase state
- keep transport orchestration separate from runtime truth ownership

Handshake/state streaming is intentionally deferred to later phases.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol
import uuid

from .cases_start import (
    ENQUETEUR_ENGINE_NAME,
    ENQUETEUR_SCHEMA_VERSION,
    CaseRunRegistry,
    StartedCaseRun,
    extract_run_id_from_connection_target,
    get_default_case_run_registry,
)

ENQUETEUR_LIVE_WS_PATH = "/live"
RUN_NOT_FOUND_WS_CLOSE_CODE = 4404
RUN_NOT_FOUND_WS_CLOSE_REASON = "RUN_NOT_FOUND"

LiveProtocolPhase = Literal["CONNECTED", "HANDSHAKING", "SUBSCRIBED", "CLOSED"]


class EnqueteurWebSocketTransport(Protocol):
    """Minimal async websocket boundary for framework adapters."""

    async def accept(self) -> None: ...

    async def close(self, code: int = 1000, reason: str = "") -> None: ...


class RunLookupError(LookupError):
    """Raised when a LIVE websocket cannot be mapped to a known started run."""

    def __init__(self, *, connection_target: str, run_id_hint: str | None = None) -> None:
        message = (
            f"No started run found for run_id={run_id_hint}."
            if run_id_hint
            else "No started run found for websocket connection target."
        )
        super().__init__(message)
        self.connection_target = connection_target
        self.run_id_hint = run_id_hint


@dataclass(frozen=True)
class EnqueteurRunBinding:
    """Stable run metadata bound to an attached websocket session."""

    run_id: str
    world_id: str
    case_id: str
    seed: str | int
    difficulty_profile: str
    mode: str
    ws_url: str
    started_at: str
    engine_name: str
    schema_version: str

    @classmethod
    def from_started_case_run(cls, record: StartedCaseRun) -> "EnqueteurRunBinding":
        return cls(
            run_id=record.run_id,
            world_id=record.world_id,
            case_id=record.request.case_id,
            seed=record.request.seed,
            difficulty_profile=record.request.difficulty_profile,
            mode=record.request.mode,
            ws_url=record.ws_url,
            started_at=record.started_at,
            engine_name=ENQUETEUR_ENGINE_NAME,
            schema_version=ENQUETEUR_SCHEMA_VERSION,
        )


@dataclass
class EnqueteurLiveSession:
    """Per-connection LIVE session container."""

    connection_id: str
    run: EnqueteurRunBinding
    phase: LiveProtocolPhase
    connected_at: str
    closed_at: str | None = None
    close_code: int | None = None
    close_reason: str | None = None


class EnqueteurLiveSessionHost:
    """Attach websocket connections to pre-started deterministic Enqueteur runs."""

    def __init__(self, *, run_registry: CaseRunRegistry | None = None) -> None:
        self._run_registry = run_registry if run_registry is not None else get_default_case_run_registry()
        self._sessions: dict[str, EnqueteurLiveSession] = {}

    def attach_connection(self, *, connection_target: str) -> EnqueteurLiveSession:
        record = self._run_registry.resolve_connection_target(connection_target)
        if record is None:
            raise RunLookupError(
                connection_target=connection_target,
                run_id_hint=extract_run_id_from_connection_target(connection_target),
            )

        session = EnqueteurLiveSession(
            connection_id=str(uuid.uuid4()),
            run=EnqueteurRunBinding.from_started_case_run(record),
            phase="CONNECTED",
            connected_at=datetime.now(UTC).isoformat(),
        )
        self._sessions[session.connection_id] = session
        return session

    def mark_handshaking(self, connection_id: str) -> EnqueteurLiveSession:
        session = self._require_session(connection_id)
        if session.phase != "CLOSED":
            session.phase = "HANDSHAKING"
        return session

    def mark_subscribed(self, connection_id: str) -> EnqueteurLiveSession:
        session = self._require_session(connection_id)
        if session.phase != "CLOSED":
            session.phase = "SUBSCRIBED"
        return session

    def close_connection(
        self,
        connection_id: str,
        *,
        close_code: int = 1000,
        close_reason: str | None = None,
    ) -> EnqueteurLiveSession:
        session = self._require_session(connection_id)
        session.phase = "CLOSED"
        session.closed_at = datetime.now(UTC).isoformat()
        session.close_code = int(close_code)
        session.close_reason = close_reason
        return session

    def get_session(self, connection_id: str) -> EnqueteurLiveSession | None:
        return self._sessions.get(connection_id)

    def list_sessions_for_run(self, run_id: str) -> tuple[EnqueteurLiveSession, ...]:
        return tuple(session for session in self._sessions.values() if session.run.run_id == run_id)

    def _require_session(self, connection_id: str) -> EnqueteurLiveSession:
        session = self._sessions.get(connection_id)
        if session is None:
            raise KeyError(f"Unknown connection_id: {connection_id}")
        return session


_DEFAULT_ENQUETEUR_LIVE_SESSION_HOST = EnqueteurLiveSessionHost()


def get_default_enqueteur_live_session_host() -> EnqueteurLiveSessionHost:
    return _DEFAULT_ENQUETEUR_LIVE_SESSION_HOST


async def open_enqueteur_live_websocket(
    websocket: EnqueteurWebSocketTransport,
    *,
    connection_target: str,
    host: EnqueteurLiveSessionHost | None = None,
) -> EnqueteurLiveSession:
    """Entrypoint for LIVE websocket attach.

    - Resolves run_id from connection_target (typically `/live?run_id=...`)
    - Attaches connection to a started deterministic run
    - Accepts websocket and marks per-connection protocol phase as HANDSHAKING
    """

    session_host = host if host is not None else get_default_enqueteur_live_session_host()
    try:
        session = session_host.attach_connection(connection_target=connection_target)
    except RunLookupError:
        await websocket.close(code=RUN_NOT_FOUND_WS_CLOSE_CODE, reason=RUN_NOT_FOUND_WS_CLOSE_REASON)
        raise

    await websocket.accept()
    session_host.mark_handshaking(session.connection_id)
    return session


__all__ = [
    "ENQUETEUR_LIVE_WS_PATH",
    "RUN_NOT_FOUND_WS_CLOSE_CODE",
    "RUN_NOT_FOUND_WS_CLOSE_REASON",
    "LiveProtocolPhase",
    "EnqueteurWebSocketTransport",
    "RunLookupError",
    "EnqueteurRunBinding",
    "EnqueteurLiveSession",
    "EnqueteurLiveSessionHost",
    "get_default_enqueteur_live_session_host",
    "open_enqueteur_live_websocket",
]
