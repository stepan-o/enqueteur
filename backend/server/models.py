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
    HELLO_VERIFIED = "HELLO_VERIFIED"
    SUBSCRIBED = "SUBSCRIBED"
    BASELINE_SENT = "BASELINE_SENT"
    LIVE = "LIVE"
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
class RunLaunchMetadata:
    run_id: str
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


@dataclass
class RunRuntimeBinding:
    started_run: Any | None = None


@dataclass
class RunHostMetadata:
    registered_at: str = field(default_factory=utc_now_iso)
    last_activity_at: str = field(default_factory=utc_now_iso)
    last_session_id: str | None = None
    active_session_id: str | None = None
    detached_at: str | None = None

    def touch(self, *, session_id: str | None = None) -> "RunHostMetadata":
        self.last_activity_at = utc_now_iso()
        if session_id is not None:
            self.last_session_id = session_id
        return self

    def attach(self, *, session_id: str) -> "RunHostMetadata":
        self.last_activity_at = utc_now_iso()
        self.last_session_id = session_id
        self.active_session_id = session_id
        self.detached_at = None
        return self

    def detach(self, *, session_id: str | None = None) -> "RunHostMetadata":
        self.last_activity_at = utc_now_iso()
        if session_id is not None:
            self.last_session_id = session_id
        self.active_session_id = None
        self.detached_at = self.last_activity_at
        return self


@dataclass
class RunRegistryEntry:
    launch: RunLaunchMetadata
    runtime: RunRuntimeBinding = field(default_factory=RunRuntimeBinding)
    host: RunHostMetadata = field(default_factory=RunHostMetadata)

    @classmethod
    def from_launch(
        cls,
        *,
        launch: RunLaunchMetadata,
        started_run: Any | None,
    ) -> "RunRegistryEntry":
        return cls(
            launch=launch,
            runtime=RunRuntimeBinding(started_run=started_run),
        )

    @property
    def run_id(self) -> str:
        return self.launch.run_id


__all__ = [
    "CaseStartTransportRequest",
    "ErrorBody",
    "RunHostMetadata",
    "RunLaunchMetadata",
    "RunRegistryEntry",
    "RunRuntimeBinding",
    "ServerHealthResponse",
    "SessionRecord",
    "SessionState",
    "new_id",
    "utc_now_iso",
]
