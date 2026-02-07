from __future__ import annotations

"""
Sprint 14.6 — State Record Exporter (Snapshots + Diffs)

Responsibilities (offline only):
- Use manifest keyframe policy and pointers to write records to disk
- Emit FULL_SNAPSHOT at keyframe ticks and FRAME_DIFF for each transition
- Apply canonicalization (Q1E3) before hashing; include schema_version in payload
- Enforce strict invariants and hash chain via prev_step_hash
 - Emit FRAME_DIFF ops[] (KVP-0001) instead of full-state diffs

No transport/session logic. Files only.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Iterable, Optional
import uuid

from .schema_version import INTEGRATION_SCHEMA_VERSION
from .canonicalize import canonicalize_state_obj
from .diff_ops import compute_state_diff_ops
from .step_hash import compute_step_hash
from .kvp_envelope import make_envelope, validate_envelope
from .record_writer import write_record
from .manifest_schema import ManifestV0_1, RecordPointer


@dataclass(frozen=True)
class StateSource:
    """Minimal interface the exporter needs: provide state objects by tick.

    State objects must already be viewer-ready primitives (dict/list/str/num/bool/None).
    No IO or simulation happens here; caller supplies deterministic data.
    """

    def get_state(self, tick: int) -> Dict[str, Any]:  # type: ignore[override]
        raise NotImplementedError


def _ensure(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _snapshot_payload(tick: int, state: Dict[str, Any]) -> Dict[str, Any]:
    can = canonicalize_state_obj(state)
    step_hash = compute_step_hash(can)
    return {
        "schema_version": INTEGRATION_SCHEMA_VERSION,
        "tick": int(tick),
        "state": can,
        "step_hash": step_hash,
    }


def _diff_payload(
    from_tick: int,
    to_tick: int,
    prev_step_hash: str,
    state_from: Dict[str, Any],
    state_to: Dict[str, Any],
) -> Dict[str, Any]:
    _ensure(to_tick == from_tick + 1, "to_tick must equal from_tick + 1")
    can_from = canonicalize_state_obj(state_from)
    can_to = canonicalize_state_obj(state_to)
    ops = compute_state_diff_ops(can_from, can_to)
    step_hash = compute_step_hash(can_to)
    return {
        "schema_version": INTEGRATION_SCHEMA_VERSION,
        "from_tick": int(from_tick),
        "to_tick": int(to_tick),
        "prev_step_hash": prev_step_hash,
        "ops": ops,
        "step_hash": step_hash,
    }


def _write_env(run_root: Path, ptr: RecordPointer, env: Dict[str, Any]) -> None:
    # Validate envelope strictly and write via single-record writer
    validate_envelope(env)
    out_path = run_root / ptr.rel_path
    write_record(out_path, env)


# Deterministic UUID namespace for exporter-generated envelopes (Sprint 14.8)
_KVP_NS = uuid.UUID("00000000-0000-5000-8000-000000000014")


def _deterministic_msg_id(*parts: Any) -> str:
    """Produce a deterministic UUIDv5 from stable string parts.

    Parts are joined with '|' and encoded as str.
    """
    name = "|".join(str(p) for p in parts)
    return str(uuid.uuid5(_KVP_NS, name))


def export_state_records(run_root: str | Path, manifest: ManifestV0_1, source: StateSource) -> None:
    """Write snapshot + diff records to disk per manifest pointers and layout.

    Strict invariants:
    - schema_version present in every payload
    - to_tick = from_tick + 1 for diffs
    - prev_step_hash matches chain (snapshot first, then prior diff)
    - canonicalization and hashing applied before writing
    - envelopes validate before file write
    """

    root = Path(run_root)

    # Determine keyframe ticks
    kf_ticks = manifest.derive_keyframe_ticks()

    # Emit snapshots at keyframes
    snapshot_hash_by_tick: Dict[int, str] = {}
    for t in kf_ticks:
        _ensure(t in manifest.snapshots, f"Missing snapshot pointer for keyframe {t}")
        ptr = manifest.snapshots[t]
        _ensure(ptr.msg_type == "FULL_SNAPSHOT", "Snapshot pointer must be FULL_SNAPSHOT")
        _ensure(ptr.tick == t, "Snapshot pointer.tick must equal keyframe tick")

        state = source.get_state(t)
        payload = _snapshot_payload(t, state)
        step_hash = payload["step_hash"]

        env = make_envelope(
            "FULL_SNAPSHOT",
            payload,
            msg_id=_deterministic_msg_id("SNAP", t),
            sent_at_ms=0,
        )
        _write_env(root, ptr, env)
        snapshot_hash_by_tick[t] = step_hash

    # Emit diffs for every transition in window using manifest inventory
    start = manifest.available_start_tick
    end = manifest.available_end_tick
    # We require diffs coverage; manifest.validate() enforces it; keep exporter strict anyway
    last_known_hash_by_tick: Dict[int, str] = {}
    # Seed the chain at each keyframe with its snapshot hash
    for t in kf_ticks:
        last_known_hash_by_tick[t] = snapshot_hash_by_tick[t]

    for from_tick in range(start, end):
        _ensure(from_tick in manifest.diffs.diffs_by_from_tick, f"Missing diff pointer for from_tick={from_tick}")
        ptr = manifest.diffs.diffs_by_from_tick[from_tick]
        _ensure(ptr.msg_type == "FRAME_DIFF", "Diff pointer must be FRAME_DIFF")
        to_tick = ptr.to_tick or (from_tick + 1)
        _ensure(to_tick == from_tick + 1, "Pointer to_tick must equal from_tick+1")

        # Determine previous step hash: nearest at or before from_tick
        # Find the most recent keyframe <= from_tick
        prev_tick_for_chain: Optional[int] = None
        for k in reversed(sorted([k for k in kf_ticks if k <= from_tick])):
            prev_tick_for_chain = k
            break
        _ensure(prev_tick_for_chain is not None, "No keyframe found at/before diff from_tick")

        # If starting a new chain at keyframe boundary, ensure we step from that point
        if from_tick == prev_tick_for_chain:
            prev_hash = snapshot_hash_by_tick[from_tick]
        else:
            # We expect previous diff to have established a hash
            _ensure((from_tick - 1) in manifest.diffs.diffs_by_from_tick or from_tick in kf_ticks,
                    "Diff chain must be contiguous")
            # prev hash must come from the prior step's hash (tick=from_tick)
            key = from_tick
            _ensure(key in last_known_hash_by_tick, "Missing prior step hash to chain from")
            prev_hash = last_known_hash_by_tick[key]

        state_from = source.get_state(from_tick)
        state_to = source.get_state(to_tick)
        payload = _diff_payload(from_tick, to_tick, prev_hash, state_from, state_to)
        env = make_envelope(
            "FRAME_DIFF",
            payload,
            msg_id=_deterministic_msg_id("DIFF", from_tick, to_tick),
            sent_at_ms=0,
        )
        _write_env(root, ptr, env)
        # Record the hash at this to_tick
        last_known_hash_by_tick[to_tick] = payload["step_hash"]


__all__ = ["StateSource", "export_state_records"]
