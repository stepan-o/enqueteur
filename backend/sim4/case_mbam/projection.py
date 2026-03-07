from __future__ import annotations

"""Projection helpers for exporting MBAM Case Truth.

These helpers provide explicit output surfaces:
- visible projection: safe to include in player-facing replay/snapshots
- debug projection: private case truth intended for DEBUG-channel artifacts only
"""

from dataclasses import asdict
from typing import Any, Mapping

from .cast_registry import FixedCastId, list_cast_ids
from .models import CaseState
from .npc_state import NPCState


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


def _sanitize_visible_behavior_flags(flags: tuple[str, ...]) -> tuple[str, ...]:
    # Keep visible behavior hints while preventing accidental leakage of
    # role/method/seed-private traces if future flags are added.
    hidden_prefixes = (
        "overlay_",
        "seed_",
        "slot_",
        "method_",
        "drop_",
        "culprit_",
        "misdirector_",
        "ally_",
    )
    return tuple(flag for flag in flags if not flag.startswith(hidden_prefixes))


def build_visible_npc_semantic_projection(
    npc_states: Mapping[FixedCastId, NPCState],
) -> list[dict[str, Any]]:
    """Build safe NPC semantic projection for replay/frontend-visible paths."""
    out: list[dict[str, Any]] = []
    for npc_id in list_cast_ids():
        state = npc_states.get(npc_id)
        if state is None:
            continue
        out.append(
            {
                "npc_id": state.npc_id,
                "current_room_id": state.current_room_id,
                "availability": state.availability,
                "trust": state.trust,
                "stress": state.stress,
                "stance": state.stance,
                "emotion": state.emotion,
                "soft_alignment_hint": state.soft_alignment_hint,
                "visible_behavior_flags": list(_sanitize_visible_behavior_flags(state.visible_behavior_flags)),
                "current_scene_id": state.current_scene_id,
                "card_state": {
                    "portrait_variant": state.card_state.portrait_variant,
                    "tell_cue": state.card_state.tell_cue,
                    "suggested_interaction_mode": state.card_state.suggested_interaction_mode,
                    "trust_trend": state.card_state.trust_trend,
                },
            }
        )
    return out


def build_debug_npc_semantic_projection(
    npc_states: Mapping[FixedCastId, NPCState],
) -> list[dict[str, Any]]:
    """Build debug/private NPC semantic projection for developer replay artifacts."""
    out: list[dict[str, Any]] = []
    for npc_id in list_cast_ids():
        state = npc_states.get(npc_id)
        if state is None:
            continue
        out.append(
            {
                "npc_id": state.npc_id,
                "overlay_role_slot": state.overlay_role_slot,
                "overlay_helpfulness": state.overlay_helpfulness,
                "current_room_id": state.current_room_id,
                "availability": state.availability,
                "trust": state.trust,
                "stress": state.stress,
                "stance": state.stance,
                "emotion": state.emotion,
                "soft_alignment_hint": state.soft_alignment_hint,
                "visible_behavior_flags": list(state.visible_behavior_flags),
                "known_fact_flags": list(state.known_fact_flags),
                "belief_flags": list(state.belief_flags),
                "hidden_flags": list(state.hidden_flags),
                "misremember_flags": list(state.misremember_flags),
                "current_scene_id": state.current_scene_id,
                "schedule_state": asdict(state.schedule_state),
                "card_state": asdict(state.card_state),
            }
        )
    return out


__all__ = [
    "build_visible_case_projection",
    "build_debug_case_projection",
    "build_visible_npc_semantic_projection",
    "build_debug_npc_semantic_projection",
]
