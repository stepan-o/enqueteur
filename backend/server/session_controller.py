from __future__ import annotations

"""Per-websocket session lifecycle shell (transport only)."""

from threading import RLock
from typing import Any

from .errors import SessionNotFoundError
from .models import SessionRecord, SessionState, new_id


class SessionController:
    """Tracks ws session records; protocol sequencing is deferred to later phases."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = RLock()

    def open_session(self, *, run_id: str | None) -> SessionRecord:
        # Keep run binding permissive until S4 attaches protocol-level validation.
        record = SessionRecord(
            connection_id=new_id(),
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

    def mark_active(self, connection_id: str) -> SessionRecord:
        record = self.require(connection_id)
        return record.transition(SessionState.ACTIVE)

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

    async def handle_incoming_text(self, *, connection_id: str, message: str) -> dict[str, Any]:
        """Placeholder ws message handling boundary for S2 protocol wiring."""
        _ = self.require(connection_id)
        _ = message
        return {
            "status": "not_implemented",
            "message": "Live protocol handling is not wired in Phase S3.",
        }

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


__all__ = ["SessionController"]
