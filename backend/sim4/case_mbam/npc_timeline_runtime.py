from __future__ import annotations

"""Deterministic MBAM timeline application onto runtime NPCState.

This module applies CaseState timeline beats to NPC semantic runtime state:
- availability transitions
- room presence changes
- schedule state progression
- stance/emotion/trust/stress scaffolding updates
"""

from dataclasses import replace

from .cast_registry import FixedCastId, list_cast_ids
from .models import CaseState, TimelineBeat
from .npc_state import (
    NPCAffectUpdate,
    NPCScheduleState,
    NPCState,
    apply_npc_affect_update,
)


def _as_npc_id(actor_id: str | None) -> FixedCastId | None:
    if actor_id is None:
        return None
    cast_ids = set(list_cast_ids())
    if actor_id in cast_ids:
        return actor_id  # type: ignore[return-value]
    return None


def _format_transition(beat: TimelineBeat) -> str:
    return f"T+{int(beat.time_offset_sec):04d}s"


def _availability_for_beat(beat: TimelineBeat, state: NPCState) -> str:
    if beat.beat_id == "T_PLUS_02_CURATOR_CONTAINMENT":
        return "busy"
    if beat.beat_id == "T_PLUS_10_DONOR_EVENT":
        if beat.location_id == "PHONE_REMOTE":
            return "busy"
        return "available"
    if beat.beat_id == "T_PLUS_15_TERMINAL_ARCHIVE":
        return "restricted"
    return state.availability


def _affect_update_for_beat(beat: TimelineBeat, state: NPCState) -> NPCAffectUpdate:
    if beat.beat_id == "T_PLUS_02_CURATOR_CONTAINMENT":
        return NPCAffectUpdate(
            stress_delta=0.10,
            stance="procedural",
            emotion="guarded",
            add_visible_behavior_flags=("beat_curator_containment",),
        )
    if beat.beat_id == "T_PLUS_05_GUARD_PATROL_SHIFT":
        return NPCAffectUpdate(
            stress_delta=0.05,
            stance="procedural",
            emotion="guarded",
            add_visible_behavior_flags=("beat_guard_patrol_shift",),
        )
    if beat.beat_id == "T_PLUS_08_INTERN_MOVEMENT":
        return NPCAffectUpdate(
            stress_delta=0.10,
            stance="flustered" if state.overlay_role_slot == "CULPRIT" else state.stance,
            emotion="nervous",
            add_visible_behavior_flags=("beat_intern_movement",),
        )
    if beat.beat_id == "T_PLUS_10_DONOR_EVENT":
        return NPCAffectUpdate(
            stress_delta=0.05,
            stance="defensive",
            emotion="guarded",
            add_visible_behavior_flags=("beat_donor_event",),
        )
    if beat.beat_id == "T_PLUS_12_BARISTA_WITNESS_WINDOW":
        return NPCAffectUpdate(
            stress_delta=-0.05,
            stance="helpful",
            emotion="calm",
            add_visible_behavior_flags=("beat_witness_window",),
        )
    if beat.beat_id == "T_PLUS_15_TERMINAL_ARCHIVE":
        return NPCAffectUpdate(
            trust_delta=-0.05,
            stress_delta=0.10,
            stance="procedural",
            emotion="annoyed",
            add_visible_behavior_flags=("beat_terminal_archive",),
        )
    return NPCAffectUpdate()


def _next_actor_beat_id(
    case_state: CaseState,
    actor_id: FixedCastId,
    applied_beat_ids: set[str],
    elapsed_seconds: float,
) -> str | None:
    beats = [
        beat
        for beat in case_state.timeline_schedule
        if beat.actor_id == actor_id
        and beat.beat_id not in applied_beat_ids
        and beat.time_offset_sec > elapsed_seconds
    ]
    if not beats:
        return None
    return sorted(beats, key=lambda b: (b.time_offset_sec, b.beat_id))[0].beat_id


def apply_case_timeline_to_npc_states(
    *,
    case_state: CaseState,
    npc_states: dict[FixedCastId, NPCState],
    elapsed_seconds: float,
    applied_beat_ids: tuple[str, ...] = (),
) -> tuple[dict[FixedCastId, NPCState], tuple[str, ...]]:
    """Apply due timeline beats to runtime NPCState map deterministically."""
    applied = set(applied_beat_ids)
    updated = dict(npc_states)

    due_beats = [
        beat
        for beat in case_state.timeline_schedule
        if beat.time_offset_sec <= elapsed_seconds and beat.beat_id not in applied
    ]
    due_beats = sorted(due_beats, key=lambda b: (b.time_offset_sec, b.beat_id))

    for beat in due_beats:
        actor_id = _as_npc_id(beat.actor_id)
        if actor_id is None:
            applied.add(beat.beat_id)
            continue

        state = updated[actor_id]
        affect_update = _affect_update_for_beat(beat, state)
        state_after_affect = apply_npc_affect_update(state, affect_update)

        next_room = beat.location_id if beat.location_id is not None else state_after_affect.current_room_id
        next_availability = _availability_for_beat(beat, state_after_affect)
        updated_state = replace(
            state_after_affect,
            current_room_id=next_room,
            availability=next_availability,  # type: ignore[arg-type]
            schedule_state=NPCScheduleState(
                current_beat_id=beat.beat_id,
                next_beat_id=state_after_affect.schedule_state.next_beat_id,
                last_transition_at=_format_transition(beat),
            ),
        )
        updated[actor_id] = updated_state
        applied.add(beat.beat_id)

    for npc_id in list_cast_ids():
        current = updated[npc_id]
        updated[npc_id] = replace(
            current,
            schedule_state=NPCScheduleState(
                current_beat_id=current.schedule_state.current_beat_id,
                next_beat_id=_next_actor_beat_id(case_state, npc_id, applied, elapsed_seconds),
                last_transition_at=current.schedule_state.last_transition_at,
            ),
        )

    return updated, tuple(sorted(applied))


__all__ = ["apply_case_timeline_to_npc_states"]
