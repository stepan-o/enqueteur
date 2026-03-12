from __future__ import annotations

"""Per-websocket session lifecycle controller for live handshake, commands, and diffs."""

import asyncio
from datetime import UTC, datetime
import json
from threading import RLock
from typing import Any
import uuid

from backend.api.live_ws import (
    EnqueteurLiveSessionHost,
    INTERNAL_RUNTIME_WS_CLOSE_CODE,
    INTERNAL_RUNTIME_WS_CLOSE_REASON,
    PROTOCOL_VIOLATION_WS_CLOSE_CODE,
    PROTOCOL_VIOLATION_WS_CLOSE_REASON,
    RunLookupError,
    handle_enqueteur_live_disconnect,
    handle_enqueteur_live_incoming_message,
    open_enqueteur_live_websocket,
    stream_enqueteur_frame_diff_loop,
)
from backend.sim4.integration.live_envelope import make_live_envelope, validate_live_envelope

from .errors import SessionNotFoundError
from .models import SessionRecord, SessionState, new_id
from .run_registry import RunRegistry

MISSING_RUN_ID_WS_CLOSE_CODE = 1008
MISSING_RUN_ID_WS_CLOSE_REASON = "MISSING_RUN_ID"
BAD_SEQUENCE_ERROR_CODE = "BAD_SEQUENCE"
BASELINE_REQUIRED_ERROR_CODE = "BASELINE_REQUIRED"
CLIENT_DISCONNECT_REASON = "CLIENT_DISCONNECT"
SESSION_CLOSED_REASON = "SESSION_CLOSED"


class SessionController:
    """Tracks ws sessions and owns /live lifecycle from handshake through interactive flow."""

    def __init__(self, *, run_registry: RunRegistry) -> None:
        self._run_registry = run_registry
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = RLock()
        self._live_host = EnqueteurLiveSessionHost(run_registry=_RunRegistryAdapter(run_registry))

    def open_session(self, *, run_id: str | None, connection_id: str | None = None) -> SessionRecord:
        record = SessionRecord(
            connection_id=connection_id or new_id(),
            run_id=run_id,
            state=SessionState.CONNECTED,
        )
        with self._lock:
            self._sessions[record.connection_id] = record
        return record

    def get(self, connection_id: str) -> SessionRecord | None:
        with self._lock:
            return self._sessions.get(connection_id)

    def require(self, connection_id: str) -> SessionRecord:
        record = self.get(connection_id)
        if record is None:
            raise SessionNotFoundError(f"Session '{connection_id}' is not tracked.")
        return record

    def mark_handshaking(self, connection_id: str) -> SessionRecord:
        record = self.require(connection_id)
        return record.transition(SessionState.HANDSHAKING)

    def mark_hello_verified(self, connection_id: str) -> SessionRecord:
        record = self.require(connection_id)
        return record.transition(SessionState.HELLO_VERIFIED)

    def mark_subscribed(self, connection_id: str) -> SessionRecord:
        record = self.require(connection_id)
        return record.transition(SessionState.SUBSCRIBED)

    def mark_baseline_sent(self, connection_id: str) -> SessionRecord:
        record = self.require(connection_id)
        return record.transition(SessionState.BASELINE_SENT)

    def mark_live(self, connection_id: str) -> SessionRecord:
        record = self.require(connection_id)
        return record.transition(SessionState.LIVE)

    def mark_closing(self, connection_id: str, *, reason: str | None = None) -> SessionRecord:
        record = self.require(connection_id)
        return record.transition(SessionState.CLOSING, close_reason=reason)

    def close_session(self, connection_id: str, *, reason: str | None = None) -> SessionRecord:
        record = self.require(connection_id)
        record.transition(SessionState.CLOSED, close_reason=reason)
        with self._lock:
            self._sessions.pop(connection_id, None)
        return record

    def list_sessions(self) -> tuple[SessionRecord, ...]:
        with self._lock:
            return tuple(self._sessions.values())

    async def serve_live_session(
        self,
        *,
        websocket: Any,
        connection_target: str | None = None,
    ) -> SessionRecord | None:
        target = connection_target or _connection_target_from_websocket(websocket)
        run_id_hint = RunRegistry.extract_run_id(target)
        if run_id_hint is None:
            await websocket.accept()
            await _send_error_envelope(
                websocket,
                code=MISSING_RUN_ID_WS_CLOSE_REASON,
                message="run_id query parameter is required for /live.",
                fatal=True,
            )
            await websocket.close(
                code=MISSING_RUN_ID_WS_CLOSE_CODE,
                reason=MISSING_RUN_ID_WS_CLOSE_REASON,
            )
            return None

        try:
            live_session = await open_enqueteur_live_websocket(
                websocket,
                connection_target=target,
                host=self._live_host,
            )
        except RunLookupError:
            return None

        record = self.open_session(
            run_id=live_session.run.run_id,
            connection_id=live_session.connection_id,
        )
        self.mark_handshaking(record.connection_id)
        termination_reason: str | None = None

        try:
            raw_hello = await websocket.receive_text()
            hello_msg_type = _extract_msg_type(raw_hello)
            if hello_msg_type is not None and hello_msg_type != "VIEWER_HELLO":
                await _close_with_error(
                    websocket,
                    code=BAD_SEQUENCE_ERROR_CODE,
                    message=f"Expected VIEWER_HELLO, got {hello_msg_type}.",
                    close_code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
                    close_reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
                )
                termination_reason = PROTOCOL_VIOLATION_WS_CLOSE_REASON
                return record
            await handle_enqueteur_live_incoming_message(
                websocket,
                session=live_session,
                raw_message=raw_hello,
                host=self._live_host,
            )
            active = self._live_host.get_session(live_session.connection_id)
            if active is None or active.phase == "CLOSED":
                termination_reason = _resolve_termination_reason(active, fallback=SESSION_CLOSED_REASON)
                return record
            if active.protocol_state != "AWAITING_SUBSCRIBE":
                await _close_with_error(
                    websocket,
                    code=BAD_SEQUENCE_ERROR_CODE,
                    message=(
                        "Expected protocol_state=AWAITING_SUBSCRIBE after VIEWER_HELLO, "
                        f"got {active.protocol_state}."
                    ),
                    close_code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
                    close_reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
                )
                termination_reason = PROTOCOL_VIOLATION_WS_CLOSE_REASON
                return record
            self.mark_hello_verified(record.connection_id)

            raw_subscribe = await websocket.receive_text()
            subscribe_msg_type = _extract_msg_type(raw_subscribe)
            if subscribe_msg_type is not None and subscribe_msg_type != "SUBSCRIBE":
                await _close_with_error(
                    websocket,
                    code=BAD_SEQUENCE_ERROR_CODE,
                    message=f"Expected SUBSCRIBE, got {subscribe_msg_type}.",
                    close_code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
                    close_reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
                )
                termination_reason = PROTOCOL_VIOLATION_WS_CLOSE_REASON
                return record
            await handle_enqueteur_live_incoming_message(
                websocket,
                session=live_session,
                raw_message=raw_subscribe,
                host=self._live_host,
            )
            active = self._live_host.get_session(live_session.connection_id)
            if active is None or active.phase == "CLOSED":
                termination_reason = _resolve_termination_reason(active, fallback=SESSION_CLOSED_REASON)
                return record
            if active.protocol_state != "SUBSCRIBED":
                await _close_with_error(
                    websocket,
                    code=BAD_SEQUENCE_ERROR_CODE,
                    message=(
                        "Expected protocol_state=SUBSCRIBED after SUBSCRIBE, "
                        f"got {active.protocol_state}."
                    ),
                    close_code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
                    close_reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
                )
                termination_reason = PROTOCOL_VIOLATION_WS_CLOSE_REASON
                return record
            self.mark_subscribed(record.connection_id)
            if not active.baseline_sent:
                await _close_with_error(
                    websocket,
                    code=BASELINE_REQUIRED_ERROR_CODE,
                    message="Live controller requires ON_JOIN baseline delivery before live-ready state.",
                    close_code=PROTOCOL_VIOLATION_WS_CLOSE_CODE,
                    close_reason=PROTOCOL_VIOLATION_WS_CLOSE_REASON,
                )
                termination_reason = PROTOCOL_VIOLATION_WS_CLOSE_REASON
                return record
            self.mark_baseline_sent(record.connection_id)
            self.mark_live(record.connection_id)
            self._touch_run_activity(record)

            while True:
                raw_live_message = await websocket.receive_text()
                live_msg_type = _extract_msg_type(raw_live_message)
                command_result = await handle_enqueteur_live_incoming_message(
                    websocket,
                    session=live_session,
                    raw_message=raw_live_message,
                    host=self._live_host,
                )
                current = self._live_host.get_session(live_session.connection_id)
                if current is None or current.phase == "CLOSED":
                    termination_reason = _resolve_termination_reason(current, fallback=SESSION_CLOSED_REASON)
                    return record
                await self._emit_command_diff_if_needed(
                    websocket=websocket,
                    live_session=live_session,
                    msg_type=live_msg_type,
                    command_result=command_result,
                )
                current = self._live_host.get_session(live_session.connection_id)
                if current is None or current.phase == "CLOSED":
                    termination_reason = _resolve_termination_reason(current, fallback=SESSION_CLOSED_REASON)
                    return record
                self._touch_run_activity(record)
            return record
        except asyncio.CancelledError:
            termination_reason = "SERVER_CANCELLED"
            raise
        except Exception as exc:  # noqa: BLE001
            if _is_websocket_disconnect(exc):
                termination_reason = CLIENT_DISCONNECT_REASON
                return record
            termination_reason = INTERNAL_RUNTIME_WS_CLOSE_REASON
            await _attempt_internal_runtime_close(websocket)
            return record
        finally:
            self._teardown_live_session(
                record=record,
                live_session=live_session,
                reason=termination_reason,
            )

    async def serve_live_handshake_baseline(
        self,
        *,
        websocket: Any,
        connection_target: str | None = None,
    ) -> SessionRecord | None:
        """Backward-compatible alias for the canonical live session entrypoint."""

        return await self.serve_live_session(
            websocket=websocket,
            connection_target=connection_target,
        )

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
        self._live_host = EnqueteurLiveSessionHost(run_registry=_RunRegistryAdapter(self._run_registry))

    def _close_tracked_session(self, connection_id: str, *, reason: str | None = None) -> None:
        if self.get(connection_id) is None:
            return
        self.mark_closing(connection_id, reason=reason)
        self.close_session(connection_id, reason=reason)

    def _touch_run_activity(self, record: SessionRecord) -> None:
        if not record.run_id:
            return
        if not self._run_registry.exists(record.run_id):
            return
        self._run_registry.touch_activity(record.run_id, session_id=record.connection_id)

    async def _emit_command_diff_if_needed(
        self,
        *,
        websocket: Any,
        live_session: Any,
        msg_type: str | None,
        command_result: Any,
    ) -> None:
        if msg_type != "INPUT_COMMAND":
            return
        if command_result is None or not bool(getattr(command_result, "accepted", False)):
            return
        await stream_enqueteur_frame_diff_loop(
            websocket,
            session=live_session,
            host=self._live_host,
            max_frames=1,
            tick_interval_seconds=0.0,
        )

    def _teardown_live_session(
        self,
        *,
        record: SessionRecord,
        live_session: Any,
        reason: str | None,
    ) -> None:
        closed = handle_enqueteur_live_disconnect(
            session=live_session,
            close_reason=reason or CLIENT_DISCONNECT_REASON,
            host=self._live_host,
        )
        close_reason = reason
        if closed is not None and isinstance(closed.close_reason, str) and closed.close_reason:
            close_reason = closed.close_reason
        self._touch_run_activity(record)
        self._close_tracked_session(record.connection_id, reason=close_reason or CLIENT_DISCONNECT_REASON)


class _RunRegistryAdapter:
    """Adapter exposing StartedCaseRun lookup from canonical server RunRegistry."""

    def __init__(self, run_registry: RunRegistry) -> None:
        self._run_registry = run_registry

    def resolve_connection_target(self, connection_target: str) -> Any | None:
        entry = self._run_registry.get_by_connection_target(connection_target)
        if entry is None:
            return None
        if RunRegistry.extract_run_id(connection_target) != entry.run_id:
            return None
        started_run = entry.runtime.started_run
        if not _is_started_case_run(started_run):
            return None
        if _extract_run_id_from_ws_url(getattr(started_run, "ws_url", None)) != entry.run_id:
            return None
        if getattr(started_run, "run_id", None) != entry.run_id:
            return None
        return started_run

    def get(self, run_id: str) -> Any | None:
        entry = self._run_registry.get(run_id)
        if entry is None:
            return None
        started_run = entry.runtime.started_run
        if not _is_started_case_run(started_run):
            return None
        if getattr(started_run, "run_id", None) != entry.run_id:
            return None
        if _extract_run_id_from_ws_url(getattr(started_run, "ws_url", None)) != entry.run_id:
            return None
        return started_run


def _is_started_case_run(value: Any) -> bool:
    return bool(
        hasattr(value, "run_id")
        and hasattr(value, "world_id")
        and hasattr(value, "request")
        and hasattr(value, "resolved_seed_id")
        and hasattr(value, "ws_url")
        and hasattr(value, "started_at")
        and hasattr(value, "runner")
    )


def _is_websocket_disconnect(exc: Exception) -> bool:
    return exc.__class__.__name__ == "WebSocketDisconnect"


def _connection_target_from_websocket(websocket: Any) -> str:
    url = getattr(websocket, "url", None)
    if url is not None:
        text = str(url).strip()
        if text:
            return text
    query_params = getattr(websocket, "query_params", None)
    if query_params is not None:
        run_id = query_params.get("run_id")
        if isinstance(run_id, str) and run_id.strip():
            return run_id.strip()
    return ""


def _extract_msg_type(raw_message: str) -> str | None:
    try:
        envelope = json.loads(raw_message)
    except json.JSONDecodeError:
        return None
    if not isinstance(envelope, dict):
        return None
    try:
        validate_live_envelope(envelope)
    except ValueError:
        return None
    msg_type = envelope.get("msg_type")
    return msg_type if isinstance(msg_type, str) else None


def _extract_run_id_from_ws_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return RunRegistry.extract_run_id(value)


async def _send_error_envelope(
    websocket: Any,
    *,
    code: str,
    message: str,
    fatal: bool,
) -> None:
    envelope = make_live_envelope(
        "ERROR",
        {
            "code": code,
            "message": message,
            "fatal": bool(fatal),
        },
        msg_id=str(uuid.uuid4()),
        sent_at_ms=int(datetime.now(UTC).timestamp() * 1000),
    )
    await websocket.send_text(json.dumps(envelope, separators=(",", ":")))


async def _close_with_error(
    websocket: Any,
    *,
    code: str,
    message: str,
    close_code: int,
    close_reason: str,
) -> None:
    await _send_error_envelope(
        websocket,
        code=code,
        message=message,
        fatal=True,
    )
    await websocket.close(code=close_code, reason=close_reason)


async def _attempt_internal_runtime_close(websocket: Any) -> None:
    try:
        await _close_with_error(
            websocket,
            code=INTERNAL_RUNTIME_WS_CLOSE_REASON,
            message="Unhandled internal runtime/session error.",
            close_code=INTERNAL_RUNTIME_WS_CLOSE_CODE,
            close_reason=INTERNAL_RUNTIME_WS_CLOSE_REASON,
        )
    except Exception:  # noqa: BLE001
        # Best-effort close; transport may already be gone.
        return


def _resolve_termination_reason(session: Any, *, fallback: str) -> str:
    close_reason = getattr(session, "close_reason", None)
    if isinstance(close_reason, str) and close_reason:
        return close_reason
    return fallback


__all__ = ["SessionController"]
