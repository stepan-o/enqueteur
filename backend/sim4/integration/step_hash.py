from __future__ import annotations

"""Stable step hashing over canonical JSON bytes (Sprint 14.2).

Provides sha256_hex(data) and compute_step_hash(state_obj) which encodes the
input using canonical JSON bytes and returns a lowercase hex digest.

No mutation of inputs; no IO or transport logic.
"""

from hashlib import sha256
from typing import Any

from .jcs import canonical_json_bytes


def sha256_hex(data: bytes) -> str:
    return sha256(data).hexdigest()


def compute_step_hash(state_obj: Any) -> str:
    """Compute a stable SHA-256 hex digest from canonical JSON bytes of obj."""
    data = canonical_json_bytes(state_obj)
    return sha256_hex(data)


__all__ = ["sha256_hex", "compute_step_hash"]
