from __future__ import annotations

"""Enqueteur LIVE WebSocket entrypoint and run-attachment host.

Phase D2 scope:
- attach incoming websocket connections to already-created runs
- enforce KVP-ENQ-0001 handshake + subscribe lifecycle
- validate protocol envelopes and sequencing via explicit state machine

State streaming and gameplay command execution are intentionally deferred.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
import json
import uuid

from backend.sim4.host.kvp_defaults import DEFAULT_ENGINE_VERSION, default_render_spec
from backend.sim4.integration.live_envelope import make_live_envelope, validate_live_envelope

from .cases_start import (
    DEFAULT_CLOCK_DT_SECONDS,
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
PROTOCOL_VIOLATION_WS_CLOSE_CODE = 1002
PROTOCOL_VIOLATION_WS_CLOSE_REASON = "PROTOCOL_VIOLATION"

ENQUETEUR_ALLOWED_CHANNELS: tuple[str, ...] = (
    "WORLD",
    "NPCS",
    "INVESTIGATION",
    "DIALOGUE",
    "LEARNING",
    "EVENTS",
    "DEBUG",
)
ALLOWED_DIFF_POLICIES: tuple[str, ...] = ("DIFF_ONLY", "PERIODIC_SNAPSHOT", "SNAPSHOT_ON_DESYNC")
ALLOWED_SNAPSHOT_POLICIES: tuple[str, ...] = ("ON_JOIN", "NEVER")
ALLOWED_COMPRESSION_POLICIES: tuple[str, ...] = ("NONE",)

LiveProtocolPhase = Literal["CONNECTED", "HANDSHAKING", "SUBSCRIBED", "CLOSED"]
LiveProtocolState = Literal["AWAITING_VIEWER_HELLO", "AWAITING_SUBSCRIBE", "SUBSCRIBED", "CLOSED"]


class EnqueteurWebSocketTransport(Protocol):
    """Minimal async websocket boundary for framework adapters."""

    async def accept(self) -> None: ...

    async def close(self, code: int = 1000, reason: str = "") -> None: ...

    async def send_text(self, data: str) -> None: ...


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


class ProtocolViolationError(ValueError):
    """Raised for invalid KVP envelopes, sequencing, or payload validation failures."""

    def __init__(self, *, code: str, message: str, fatal: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fatal = bool(fatal)


@dataclass(frozen=True)
class EnqueteurViewerHello:
    viewer_name: str
    viewer_version: str
    supported_schema_versions: tuple[str, ...]
    supports: dict[str, Any]


@dataclass(frozen=True)
class EnqueteurSubscribedConfig:
    stream_id: str
    effective_stream: str
    effective_channels: tuple[str, ...]
    effective_diff_policy: str
    effective_snapshot_policy: str
    effective_compression: str


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
    engine_version: str
    schema_version: str
    tick_rate_hz: int
    time_origin_ms: int
    render_spec: dict[str, Any]

    @classmethod
    def from_started_case_run(cls, record: StartedCaseRun) -> "EnqueteurRunBinding":
        tick_rate_hz = int(round(1.0 / DEFAULT_CLOCK_DT_SECONDS))
        if tick_rate_hz <= 0:
            raise ValueError("DEFAULT_CLOCK_DT_SECONDS must resolve to a positive tick_rate_hz")

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
            engine_version=DEFAULT_ENGINE_VERSION,
            schema_version=ENQUETEUR_SCHEMA_VERSION,
            tick_rate_hz=tick_rate_hz,
            time_origin_ms=0,
            render_spec=default_render_spec().to_dict(),
        )


@dataclass
class EnqueteurLiveSession:
    """Per-connection LIVE session container with explicit protocol state."""

    connection_id: str
    run: EnqueteurRunBinding
    phase: LiveProtocolPhase
    protocol_state: LiveProtocolState
    connected_at: str
    viewer_hello: EnqueteurViewerHello | None = None
    subscribed_config: EnqueteurSubscribedConfig | None = None
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
            protocol_state="AWAITING_VIEWER_HELLO",
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
            session.protocol_state = "SUBSCRIBED"
        return session

    def record_viewer_hello(self, connection_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        session = self._require_session(connection_id)
        self._require_protocol_state(session, "AWAITING_VIEWER_HELLO", action="VIEWER_HELLO")

        viewer_name = _require_non_empty_str(payload.get("viewer_name"), field="viewer_name", code="INVALID_VIEWER_HELLO")
        viewer_version = _require_non_empty_str(
            payload.get("viewer_version"),
            field="viewer_version",
            code="INVALID_VIEWER_HELLO",
        )
        supported_schema_versions = _require_string_list(
            payload.get("supported_schema_versions"),
            field="supported_schema_versions",
            code="INVALID_VIEWER_HELLO",
            non_empty=True,
        )
        if ENQUETEUR_SCHEMA_VERSION not in supported_schema_versions:
            raise ProtocolViolationError(
                code="SCHEMA_MISMATCH",
                message=(
                    "Viewer does not support schema_version="
                    f"{ENQUETEUR_SCHEMA_VERSION}."
                ),
                fatal=True,
            )

        supports = payload.get("supports", {})
        if not isinstance(supports, dict):
            raise ProtocolViolationError(
                code="INVALID_VIEWER_HELLO",
                message="supports must be an object when provided.",
                fatal=True,
            )

        session.viewer_hello = EnqueteurViewerHello(
            viewer_name=viewer_name,
            viewer_version=viewer_version,
            supported_schema_versions=tuple(supported_schema_versions),
            supports=dict(supports),
        )
        session.protocol_state = "AWAITING_SUBSCRIBE"

        return {
            "engine_name": session.run.engine_name,
            "engine_version": session.run.engine_version,
            "schema_version": session.run.schema_version,
            "world_id": session.run.world_id,
            "run_id": session.run.run_id,
            "seed": session.run.seed,
            "tick_rate_hz": session.run.tick_rate_hz,
            "time_origin_ms": session.run.time_origin_ms,
            "render_spec": session.run.render_spec,
        }

    def record_subscribe(self, connection_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        session = self._require_session(connection_id)
        self._require_protocol_state(session, "AWAITING_SUBSCRIBE", action="SUBSCRIBE")

        stream = _require_non_empty_str(payload.get("stream"), field="stream", code="INVALID_SUBSCRIPTION")
        if stream != "LIVE":
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message="SUBSCRIBE.stream must be LIVE.",
                fatal=True,
            )

        channels = _require_string_list(
            payload.get("channels"),
            field="channels",
            code="INVALID_SUBSCRIPTION",
            non_empty=True,
        )
        if len(set(channels)) != len(channels):
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message="SUBSCRIBE.channels must not contain duplicates.",
                fatal=True,
            )
        unknown = [c for c in channels if c not in ENQUETEUR_ALLOWED_CHANNELS]
        if unknown:
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message=f"SUBSCRIBE.channels contains unsupported values: {', '.join(unknown)}.",
                fatal=True,
            )

        diff_policy = str(payload.get("diff_policy", "DIFF_ONLY"))
        snapshot_policy = str(payload.get("snapshot_policy", "ON_JOIN"))
        compression = str(payload.get("compression", "NONE"))
        if diff_policy not in ALLOWED_DIFF_POLICIES:
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message=f"Unsupported diff_policy '{diff_policy}'.",
                fatal=True,
            )
        if snapshot_policy not in ALLOWED_SNAPSHOT_POLICIES:
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message=f"Unsupported snapshot_policy '{snapshot_policy}'.",
                fatal=True,
            )
        if compression not in ALLOWED_COMPRESSION_POLICIES:
            raise ProtocolViolationError(
                code="INVALID_SUBSCRIPTION",
                message=f"Unsupported compression '{compression}'.",
                fatal=True,
            )

        config = EnqueteurSubscribedConfig(
            stream_id=str(uuid.uuid4()),
            effective_stream="LIVE",
            effective_channels=tuple(channels),
            effective_diff_policy=diff_policy,
            effective_snapshot_policy=snapshot_policy,
            effective_compression=compression,
        )
        session.subscribed_config = config
        self.mark_subscribed(connection_id)

        return {
            "stream_id": config.stream_id,
            "effective_stream": config.effective_stream,
            "effective_channels": list(config.effective_channels),
            "effective_diff_policy": config.effective_diff_policy,
            "effective_snapshot_policy": config.effective_snapshot_policy,
            "effective_compression": config.effective_compression,
        }

    def can_deliver_state(self, connection_id: str) -> bool:
        session = self._require_session(connection_id)
        return session.protocol_state == "SUBSCRIBED" and session.phase == "SUBSCRIBED"

    def close_connection(
        self,
        connection_id: str,
        *,
        close_code: int = 1000,
        close_reason: str | None = None,
    ) -> EnqueteurLiveSession:
        session = self._require_session(connection_id)
        session.phase = "CLOSED"
        session.protocol_state = "CLOSED"
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

    def _require_protocol_state(
        self,
        session: EnqueteurLiveSession,
        expected_state: LiveProtocolState,
        *,
        action: str,
    ) -> None:
        if session.protocol_state != expected_state:
            raise ProtocolViolationError(
                code="BAD_SEQUENCE",
                message=(
                    f"{action} received while protocol_state={session.protocol_state}; "
                    f"expected {expected_state}."
                ),
                fatal=True,
            )


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

    - resolves run_id from connection_target (typically `/live?run_id=...`)
    - attaches connection to a started deterministic run
    - accepts websocket and prepares state machine for VIEWER_HELLO
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


async def handle_enqueteur_live_incoming_message(
    websocket: EnqueteurWebSocketTransport,
    *,
    session: EnqueteurLiveSession,
    raw_message: str | bytes,
    host: EnqueteurLiveSessionHost | None = None,
) -> None:
    """Handle one inbound websocket message using strict KVP envelope dispatch."""

    session_host = host if host is not None else get_default_enqueteur_live_session_host()
    try:
        envelope = _decode_incoming_envelope(raw_message)
        msg_type = envelope["msg_type"]
        payload = envelope["payload"]

        if msg_type == "VIEWER_HELLO":
            kernel_hello = session_host.record_viewer_hello(session.connection_id, payload)
            await _send_envelope(websocket, msg_type="KERNEL_HELLO", payload=kernel_hello)
            return

        if msg_type == "SUBSCRIBE":
            subscribed = session_host.record_subscribe(session.connection_id, payload)
            await _send_envelope(websocket, msg_type="SUBSCRIBED", payload=subscribed)
            return

        if not session_host.can_deliver_state(session.connection_id):
            raise ProtocolViolationError(
                code="BAD_SEQUENCE",
                message=f"{msg_type} is not allowed before SUBSCRIBED.",
                fatal=True,
            )

        raise ProtocolViolationError(
            code="UNSUPPORTED_MESSAGE",
            message=f"Unsupported msg_type: {msg_type}.",
            fatal=False,
        )

    except ProtocolViolationError as exc:
        await _send_error(websocket, code=exc.code, message=exc.message, fatal=exc.fatal)
        if exc.fatal:
            session_host.close_connection(
                session.connection_id,
                close_code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
                close_reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
            )
            await websocket.close(
                code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
                reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
            )
    except Exception as exc:  # noqa: BLE001
        await _send_error(
            websocket,
            code="INVALID_ENVELOPE",
            message=f"Invalid live envelope: {exc}",
            fatal=True,
        )
        session_host.close_connection(
            session.connection_id,
            close_code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
            close_reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
        )
        await websocket.close(
            code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
            reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
        )


async def _send_envelope(websocket: EnqueteurWebSocketTransport, *, msg_type: str, payload: dict[str, Any]) -> None:
    envelope = make_live_envelope(
        msg_type,
        payload,
        msg_id=str(uuid.uuid4()),
        sent_at_ms=int(datetime.now(UTC).timestamp() * 1000),
    )
    await websocket.send_text(json.dumps(envelope, separators=(",", ":")))


async def _send_error(
    websocket: EnqueteurWebSocketTransport,
    *,
    code: str,
    message: str,
    fatal: bool,
) -> None:
    await _send_envelope(
        websocket,
        msg_type="ERROR",
        payload={
            "code": code,
            "message": message,
            "fatal": bool(fatal),
        },
    )


def _decode_incoming_envelope(raw_message: str | bytes) -> dict[str, Any]:
    text = raw_message.decode("utf-8") if isinstance(raw_message, bytes) else raw_message
    if not isinstance(text, str):
        raise ValueError("Inbound websocket message must be UTF-8 text.")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Inbound websocket message must decode to an object envelope.")
    validate_live_envelope(parsed)
    return parsed


def _require_non_empty_str(value: Any, *, field: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolViolationError(code=code, message=f"{field} must be a non-empty string.", fatal=True)
    return value.strip()


def _require_string_list(
    value: Any,
    *,
    field: str,
    code: str,
    non_empty: bool,
) -> list[str]:
    if not isinstance(value, list):
        raise ProtocolViolationError(code=code, message=f"{field} must be a list.", fatal=True)
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ProtocolViolationError(code=code, message=f"{field} must contain non-empty strings.", fatal=True)
        out.append(item.strip())
    if non_empty and not out:
        raise ProtocolViolationError(code=code, message=f"{field} must be non-empty.", fatal=True)
    return out


__all__ = [
    "ENQUETEUR_LIVE_WS_PATH",
    "RUN_NOT_FOUND_WS_CLOSE_CODE",
    "RUN_NOT_FOUND_WS_CLOSE_REASON",
    "PROTOCOL_VIOLATION_WS_CLOSE_CODE",
    "PROTOCOL_VIOLATION_WS_CLOSE_REASON",
    "ENQUETEUR_ALLOWED_CHANNELS",
    "LiveProtocolPhase",
    "LiveProtocolState",
    "EnqueteurWebSocketTransport",
    "RunLookupError",
    "ProtocolViolationError",
    "EnqueteurViewerHello",
    "EnqueteurSubscribedConfig",
    "EnqueteurRunBinding",
    "EnqueteurLiveSession",
    "EnqueteurLiveSessionHost",
    "get_default_enqueteur_live_session_host",
    "open_enqueteur_live_websocket",
    "handle_enqueteur_live_incoming_message",
]
