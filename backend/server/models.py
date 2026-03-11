from __future__ import annotations

"""Transport-facing data models for the server shell layer."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class ErrorBody:
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass(frozen=True)
class ServerHealthResponse:
    status: str
    service: str
    started_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "service": self.service,
            "started_at": self.started_at,
        }


@dataclass(frozen=True)
class PlaceholderCaseStartRequest:
    case_id: str | None = None
    seed: str | int | None = None
    difficulty_profile: str | None = None
    mode: str | None = None


@dataclass(frozen=True)
class PlaceholderCaseStartResponse:
    status: str = "not_implemented"
    message: str = "Case launch wiring is not implemented in Phase S1."

    def to_dict(self) -> dict[str, str]:
        return {"status": self.status, "message": self.message}


class SessionState(StrEnum):
    CONNECTED = "CONNECTED"
    HANDSHAKING = "HANDSHAKING"
    ACTIVE = "ACTIVE"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


@dataclass
class SessionRecord:
    connection_id: str
    run_id: str | None
    state: SessionState
    connected_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    close_reason: str | None = None

    def transition(self, state: SessionState, *, close_reason: str | None = None) -> "SessionRecord":
        self.state = state
        self.updated_at = utc_now_iso()
        if close_reason is not None:
            self.close_reason = close_reason
        return self


@dataclass
class RunRecord:
    run_id: str
    created_at: str = field(default_factory=utc_now_iso)
    case_id: str | None = None
    seed: str | int | None = None
    difficulty_profile: str | None = None
    mode: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "ErrorBody",
    "PlaceholderCaseStartRequest",
    "PlaceholderCaseStartResponse",
    "RunRecord",
    "ServerHealthResponse",
    "SessionRecord",
    "SessionState",
    "new_id",
    "utc_now_iso",
]

