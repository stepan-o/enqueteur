from __future__ import annotations

"""Single-record JSON writer for KVP envelopes (Sprint 14.3).

Writes exactly one JSON object per file (UTF-8, no BOM, compact).
Validates the envelope using validate_envelope() before writing.

Includes a tiny read_record() helper for tests.
"""

from pathlib import Path
from typing import Any, Dict
import json

from .kvp_envelope import validate_envelope


def write_record(path: str | Path, envelope: Dict[str, Any]) -> None:
    """Write a single KVP envelope JSON object to path.

    - Validates envelope first
    - Writes UTF-8 without BOM
    - Compact JSON (no spaces/newlines besides what json adds minimally)
    """
    validate_envelope(envelope)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Ensure compact separators and stable key order is not required for correctness here,
    # but we keep it compact and deterministic enough.
    data = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)
    # Encode explicitly as UTF-8 and write bytes to avoid BOM
    p.write_bytes(data.encode("utf-8"))


def read_record(path: str | Path) -> Dict[str, Any]:
    """Read a single JSON object from path and return as dict."""
    p = Path(path)
    raw = p.read_bytes()
    # Assert not starting with BOM for tests (decode will also handle but we want guardrail)
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("File must not start with UTF-8 BOM")
    text = raw.decode("utf-8")
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("Record file must contain a single JSON object")
    return obj


__all__ = ["write_record", "read_record"]
