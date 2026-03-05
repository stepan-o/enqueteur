from __future__ import annotations

"""KVP envelope construction and validation (Sprint 14.3).

Rules enforced here are guardrails for artifacts-only records:
- kvp_version comes from SSoT KVP_VERSION
- msg_type is authoritative discriminator and must be allowed and SCREAMING_SNAKE_CASE
- payload must be a dict
- msg_id must be a non-empty string (uuid-like optional)
- sent_at_ms must be int >= 0

No transport/session/REPLAY_* logic is permitted.
"""

from typing import Any, Dict, Final, Iterable
import re
import uuid as _uuid

from .kvp_version import KVP_VERSION


# Allowed artifact message types for Sprint 14.
# Envelope-level guardrail: includes X_* overlays because those are still
# standalone envelopes, even though they are not referenced as state pointers.
ALLOWED_ARTIFACT_MSG_TYPES: Final[set[str]] = {
    "FULL_SNAPSHOT",
    "FRAME_DIFF",
    # Allow KERNEL_HELLO now (when serialized as an artifact later)
    "KERNEL_HELLO",
    # Overlay sidecars (out-of-protocol X_* streams; S14.7)
    "X_UI_EVENT_BATCH",
    "X_PSYCHO_FRAME",
    "X_STATIC_MAP",
}

# Explicit forbidden prefixes (live/session)
FORBIDDEN_PREFIXES: Final[tuple[str, ...]] = ("REPLAY_",)

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
    # Optional UUID-ish validation (best-effort, do not overengineer)
    try:
        _uuid.UUID(s)
    except Exception:  # noqa: BLE001
        # Accept non-UUID strings but encourage UUIDs: keep strict but with a clear error
        # For Sprint 14, we will enforce UUID format to keep artifacts clean.
        raise ValueError("msg_id must be a valid UUID string")


def make_envelope(msg_type: str, payload: Dict[str, Any], *, msg_id: str, sent_at_ms: int) -> Dict[str, Any]:
    """Construct a strict KVP envelope dict.

    Args:
        msg_type: Artifact message type in SCREAMING_SNAKE_CASE. Must be one of
            ALLOWED_ARTIFACT_MSG_TYPES and must not start with any FORBIDDEN_PREFIXES.
        payload: Message payload as a dictionary. Must be a dict; content is not
            validated here beyond type.
        msg_id: Unique identifier for the message. Must be a valid UUID string.
        sent_at_ms: Send timestamp in milliseconds since epoch. Must be an integer >= 0.

    Returns:
        A new envelope dictionary with keys: kvp_version, msg_type, msg_id,
        sent_at_ms, payload. The function performs final validation before
        returning the envelope.

    Raises:
        ValueError: If any of the input arguments violate envelope rules (e.g.,
            unknown msg_type, non-dict payload, non-UUID msg_id, or negative/non-int sent_at_ms).
    """
    # msg_type rules
    if not isinstance(msg_type, str) or not msg_type:
        raise ValueError("msg_type must be a non-empty string")
    if not _is_screaming_snake(msg_type):
        raise ValueError("msg_type must be SCREAMING_SNAKE_CASE (A-Z, 0-9, underscore)")
    for p in FORBIDDEN_PREFIXES:
        if msg_type.startswith(p):
            raise ValueError("msg_type starting with forbidden prefix: " + p)
    if msg_type not in ALLOWED_ARTIFACT_MSG_TYPES:
        raise ValueError("msg_type not allowed in Sprint 14 artifacts: " + msg_type)

    # payload rules
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")

    # msg_id
    _validate_msg_id(msg_id)

    # sent_at_ms
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
    # Final validation pass to keep a single source of truth for checks
    validate_envelope(env)
    return env


def validate_envelope(envelope: Dict[str, Any]) -> None:
    """Validate an envelope dict in-place.

    Args:
        envelope: Envelope dictionary to validate. Must include keys
            kvp_version, msg_type, msg_id, sent_at_ms, and payload.

    Raises:
        ValueError: If the envelope is missing required keys or any field fails
            validation (version mismatch, msg_type shape/allow-list, msg_id UUID,
            sent_at_ms integer >= 0, payload is a dict).
    """
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a dict")
    _require_keys(envelope, ["kvp_version", "msg_type", "msg_id", "sent_at_ms", "payload"])

    # kvp_version
    if envelope["kvp_version"] != KVP_VERSION:
        raise ValueError("kvp_version mismatch with SSoT KVP_VERSION")

    # msg_type
    mt = envelope.get("msg_type")
    if not isinstance(mt, str) or not mt:
        raise ValueError("msg_type must be a non-empty string")
    if not _is_screaming_snake(mt):
        raise ValueError("msg_type must be SCREAMING_SNAKE_CASE (A-Z, 0-9, underscore)")
    for p in FORBIDDEN_PREFIXES:
        if mt.startswith(p):
            raise ValueError("msg_type starting with forbidden prefix: " + p)
    if mt not in ALLOWED_ARTIFACT_MSG_TYPES:
        raise ValueError("msg_type not allowed in Sprint 14 artifacts: " + mt)

    # msg_id
    _validate_msg_id(envelope["msg_id"])  # type: ignore[arg-type]

    # sent_at_ms
    try:
        sent_int = int(envelope["sent_at_ms"])  # type: ignore[arg-type]
    except Exception as e:  # noqa: BLE001
        raise ValueError("sent_at_ms must be an integer") from e
    if sent_int < 0:
        raise ValueError("sent_at_ms must be >= 0")

    # payload
    if not isinstance(envelope["payload"], dict):
        raise ValueError("payload must be a dict")


def envelope_msg_type(envelope: Dict[str, Any]) -> str:
    """Return the envelope msg_type; raises if missing/invalid.

    Args:
        envelope: Envelope dictionary to inspect. Must contain a non-empty
            string field "msg_type".

    Returns:
        The msg_type string extracted from the envelope.

    Raises:
        ValueError: If envelope is not a dict, lacks msg_type, or msg_type is
            not a non-empty string.

    Notes:
        This function intentionally consults only msg_type and not payload shape
        to enforce envelope-first dispatch.
    """
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a dict")
    if "msg_type" not in envelope:
        raise ValueError("envelope missing msg_type")
    mt = envelope["msg_type"]
    if not isinstance(mt, str) or not mt:
        raise ValueError("msg_type must be a non-empty string")
    return mt


__all__ = [
    "ALLOWED_ARTIFACT_MSG_TYPES",
    "FORBIDDEN_PREFIXES",
    "make_envelope",
    "validate_envelope",
    "envelope_msg_type",
]
