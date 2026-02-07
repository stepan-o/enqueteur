from __future__ import annotations

"""
Sprint 14.6 — Export Verifier (offline, deterministic)

Verifies exported artifacts using the manifest pointers:
- Loads nearest keyframe snapshot <= target tick
- Applies per‑tick ops-based diffs sequentially up to target
- Validates: envelope shape, payload schema_version, tick continuity,
  to_tick == from_tick+1, prev_step_hash chain, and canonical step_hash.

No kernel/runtime/session imports. Files only.
"""

from pathlib import Path
from typing import Dict, Any, Tuple

from .schema_version import INTEGRATION_SCHEMA_VERSION
from .manifest_schema import ManifestV0_1
from .record_writer import read_record
from .kvp_envelope import validate_envelope
from .step_hash import compute_step_hash
from .diff_ops import apply_state_diff_ops


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _nearest_keyframe(manifest: ManifestV0_1, target_tick: int) -> int:
    ticks = [t for t in manifest.derive_keyframe_ticks() if t <= target_tick]
    _require(len(ticks) > 0, "No keyframe at or before target tick")
    return max(ticks)


def _load_envelope(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    env = read_record(path)
    validate_envelope(env)
    return env


def _verify_snapshot_payload(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str, int]:
    _require(isinstance(payload, dict), "snapshot payload must be a dict")
    _require(payload.get("schema_version") == INTEGRATION_SCHEMA_VERSION, "schema_version missing/invalid in snapshot")
    _require("state" in payload, "snapshot payload missing state")
    _require("step_hash" in payload and isinstance(payload["step_hash"], str), "snapshot missing step_hash")
    state = payload["state"]
    step_hash = payload["step_hash"]
    # recompute step hash over state
    recomputed = compute_step_hash(state)
    _require(recomputed == step_hash, "snapshot step_hash does not match canonical bytes")
    tick = int(payload.get("tick", -1))
    _require(tick >= 0, "snapshot tick missing/invalid")
    return state, step_hash, tick


def _verify_diff_payload(
    payload: Dict[str, Any],
    prev_step_hash: str,
    state_before: Dict[str, Any],
) -> Tuple[Dict[str, Any], str, int, int]:
    _require(isinstance(payload, dict), "diff payload must be a dict")
    _require(payload.get("schema_version") == INTEGRATION_SCHEMA_VERSION, "schema_version missing/invalid in diff")
    _require("from_tick" in payload and "to_tick" in payload, "diff missing from/to tick")
    ft = int(payload["from_tick"])  # type: ignore[arg-type]
    tt = int(payload["to_tick"])  # type: ignore[arg-type]
    _require(tt == ft + 1, "diff to_tick must equal from_tick + 1")
    _require(payload.get("prev_step_hash") == prev_step_hash, "diff prev_step_hash does not match chain")
    _require("ops" in payload and "step_hash" in payload, "diff missing ops/step_hash")
    ops = payload["ops"]
    step_hash = payload["step_hash"]
    # Apply ops to reconstruct state
    state = apply_state_diff_ops(state_before, ops)
    recomputed = compute_step_hash(state)
    _require(recomputed == step_hash, "diff step_hash does not match canonical bytes")
    return state, step_hash, ft, tt


def reconstruct_state_at_tick(run_root: str | Path, manifest: ManifestV0_1, target_tick: int) -> Dict[str, Any]:
    """Reconstruct state for target_tick using manifest pointers.

    Returns the reconstructed state dict; raises on any validation failure.
    """
    root = Path(run_root)
    _require(manifest.available_start_tick <= target_tick <= manifest.available_end_tick,
             "target_tick outside available range")

    kf = _nearest_keyframe(manifest, target_tick)
    # Load snapshot envelope
    snap_ptr = manifest.snapshots[kf]
    snap_env = _load_envelope(root / snap_ptr.rel_path)
    _require(snap_env.get("msg_type") == "FULL_SNAPSHOT", "snapshot envelope msg_type must be FULL_SNAPSHOT")
    state, step_hash, tick = _verify_snapshot_payload(snap_env["payload"])  # type: ignore[index]
    _require(tick == kf, "snapshot payload.tick must equal keyframe tick")

    # Apply diffs up to target
    cur_state = state
    cur_hash = step_hash
    cur_tick = kf
    while cur_tick < target_tick:
        ptr = manifest.diffs.diffs_by_from_tick.get(cur_tick)
        _require(ptr is not None, f"Missing diff for from_tick={cur_tick}")
        env = _load_envelope(root / ptr.rel_path)
        _require(env.get("msg_type") == "FRAME_DIFF", "diff envelope msg_type must be FRAME_DIFF")
        cur_state, cur_hash, ft, tt = _verify_diff_payload(env["payload"], cur_hash, cur_state)  # type: ignore[index]
        _require(ft == cur_tick and tt == cur_tick + 1, "diff transition does not match expected ticks")
        cur_tick = tt

    return cur_state


__all__ = ["reconstruct_state_at_tick"]
