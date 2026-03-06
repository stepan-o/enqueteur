from __future__ import annotations

"""Projection helpers for exporting MBAM Case Truth.

These helpers provide explicit output surfaces:
- visible projection: safe to include in player-facing replay/snapshots
- debug projection: private case truth intended for DEBUG-channel artifacts only
"""

from dataclasses import asdict
from typing import Any

from .models import CaseState


def _require_positive_epoch(truth_epoch: int) -> int:
    epoch = int(truth_epoch)
    if epoch <= 0:
        raise ValueError("truth_epoch must be >= 1")
    return epoch


def build_visible_case_projection(case_state: CaseState, *, truth_epoch: int = 1) -> dict[str, Any]:
    """Build the minimal visible case projection for snapshots/exports."""
    epoch = _require_positive_epoch(truth_epoch)
    visible_slice = case_state.visible_case_slice
    return {
        "case_id": case_state.case_id,
        "seed": case_state.seed,
        "truth_epoch": epoch,
        "visible_case_slice": {
            "public_room_ids": list(visible_slice.public_room_ids),
            "public_object_ids": list(visible_slice.public_object_ids),
            "starting_scene_id": visible_slice.starting_scene_id,
            "starting_known_fact_ids": list(visible_slice.starting_known_fact_ids),
        },
    }


def build_debug_case_projection(case_state: CaseState, *, truth_epoch: int = 1) -> dict[str, Any]:
    """Build private case-truth projection for DEBUG-only exports."""
    epoch = _require_positive_epoch(truth_epoch)
    return {
        "case_id": case_state.case_id,
        "seed": case_state.seed,
        "truth_epoch": epoch,
        "debug_scope": "case_truth_private",
        "roles_assignment": asdict(case_state.roles_assignment),
        "hidden_case_slice": {
            "private_fact_ids": list(case_state.hidden_case_slice.private_fact_ids),
            "private_overlay_flags": list(case_state.hidden_case_slice.private_overlay_flags),
        },
    }


__all__ = ["build_visible_case_projection", "build_debug_case_projection"]
