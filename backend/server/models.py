from __future__ import annotations

"""Transport-facing data models for the server shell layer."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping
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
class CaseStartTransportRequest:
    """Transport-facing launch request envelope (core validation stays in backend.api.cases_start)."""

    case_id: Any = None
    seed: Any = None
    difficulty_profile: Any = None
    mode: Any = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "CaseStartTransportRequest":
        return cls(
            case_id=payload.get("case_id"),
            seed=payload.get("seed"),
            difficulty_profile=payload.get("difficulty_profile"),
            mode=payload.get("mode"),
        )

    def to_core_payload(self) -> dict[str, Any]:
        payload = {
            "case_id": self.case_id,
            "seed": self.seed,
            "difficulty_profile": self.difficulty_profile,
        }
        if self.mode is not None:
            payload["mode"] = self.mode
        return payload


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
    world_id: str | None = None
    case_id: str | None = None
    seed: str | int | None = None
    resolved_seed_id: str | None = None
    difficulty_profile: str | None = None
    mode: str | None = None
    engine_name: str | None = None
    schema_version: str | None = None
    ws_url: str | None = None
    started_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    launch_payload: dict[str, Any] = field(default_factory=dict)
    started_run: Any | None = None


__all__ = [
    "CaseStartTransportRequest",
    "ErrorBody",
    "RunRecord",
    "ServerHealthResponse",
    "SessionRecord",
    "SessionState",
    "new_id",
    "utc_now_iso",
]
