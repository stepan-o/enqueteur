from __future__ import annotations

"""KVP live-session envelope helpers (v0.1).

This module mirrors the artifact envelope shape but allows the full set of
LIVE message types (handshake, subscribe, state delivery, input, replay,
desync, errors). It is intentionally separate from kvp_envelope.py, which is
artifact-only and stricter.
"""

from typing import Any, Dict, Final, Iterable
import re
import uuid as _uuid

from .kvp_version import KVP_VERSION


ALLOWED_LIVE_MSG_TYPES: Final[set[str]] = {
    # Handshake/session
    "VIEWER_HELLO",
    "KERNEL_HELLO",
    "SUBSCRIBE",
    "SUBSCRIBED",
    "UNSUBSCRIBE",
    "PING",
    "PONG",
    # State delivery
    "FULL_SNAPSHOT",
    "FRAME_DIFF",
    # Input
    "SIM_INPUT",
    "INPUT_COMMAND",
    "COMMAND_ACCEPTED",
    "COMMAND_REJECTED",
    # Replay control (LIVE transport only)
    "REPLAY_BEGIN",
    "REPLAY_READY",
    "REPLAY_SEEK",
    "REPLAY_END",
    # Debug/recovery
    "DEBUG_PROBE",
    "DEBUG_PROBE_RESULT",
    "DESYNC_REPORT",
    "DESYNC_CONFIRMED",
    "DESYNC_DENIED",
    # Errors
    "WARN",
    "ERROR",
}

_SNAKE_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _is_screaming_snake(s: str) -> bool:
    return bool(_SNAKE_RE.match(s))


def _ensure(condition: bool, msg: str) -> None:
    if not condition:
        raise ValueError(msg)


def _require_keys(obj: Dict[str, Any], keys: Iterable[str]) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise ValueError("Envelope missing required keys: " + ", ".join(missing))


def _validate_msg_id(s: str) -> None:
    _ensure(isinstance(s, str) and len(s) > 0, "msg_id must be a non-empty string")
    try:
        _uuid.UUID(s)
    except Exception as e:  # noqa: BLE001
        raise ValueError("msg_id must be a valid UUID string") from e


def make_live_envelope(msg_type: str, payload: Dict[str, Any], *, msg_id: str, sent_at_ms: int) -> Dict[str, Any]:
    """Construct a live-session envelope dict (v0.1)."""
    if not isinstance(msg_type, str) or not msg_type:
        raise ValueError("msg_type must be a non-empty string")
    if not _is_screaming_snake(msg_type):
        raise ValueError("msg_type must be SCREAMING_SNAKE_CASE (A-Z, 0-9, underscore)")
    if msg_type not in ALLOWED_LIVE_MSG_TYPES:
        raise ValueError("msg_type not allowed for LIVE session: " + msg_type)
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    _validate_msg_id(msg_id)
    try:
        sent_int = int(sent_at_ms)
    except Exception as e:  # noqa: BLE001
        raise ValueError("sent_at_ms must be an integer") from e
    if sent_int < 0:
        raise ValueError("sent_at_ms must be >= 0")
    env = {
        "kvp_version": KVP_VERSION,
        "msg_type": msg_type,
        "msg_id": msg_id,
        "sent_at_ms": sent_int,
        "payload": payload,
    }
    validate_live_envelope(env)
    return env


def validate_live_envelope(envelope: Dict[str, Any]) -> None:
    """Validate a live-session envelope dict. Raises ValueError if invalid."""
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a dict")
    _require_keys(envelope, ["kvp_version", "msg_type", "msg_id", "sent_at_ms", "payload"])
    if envelope["kvp_version"] != KVP_VERSION:
        raise ValueError("kvp_version mismatch with SSoT KVP_VERSION")
    mt = envelope.get("msg_type")
    if not isinstance(mt, str) or not mt:
        raise ValueError("msg_type must be a non-empty string")
    if not _is_screaming_snake(mt):
        raise ValueError("msg_type must be SCREAMING_SNAKE_CASE (A-Z, 0-9, underscore)")
    if mt not in ALLOWED_LIVE_MSG_TYPES:
        raise ValueError("msg_type not allowed for LIVE session: " + mt)
    _validate_msg_id(envelope["msg_id"])  # type: ignore[arg-type]
    try:
        sent_int = int(envelope["sent_at_ms"])  # type: ignore[arg-type]
    except Exception as e:  # noqa: BLE001
        raise ValueError("sent_at_ms must be an integer") from e
    if sent_int < 0:
        raise ValueError("sent_at_ms must be >= 0")
    if not isinstance(envelope["payload"], dict):
        raise ValueError("payload must be a dict")


__all__ = ["ALLOWED_LIVE_MSG_TYPES", "make_live_envelope", "validate_live_envelope"]
