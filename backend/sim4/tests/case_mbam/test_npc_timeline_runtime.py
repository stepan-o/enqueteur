from __future__ import annotations

from backend.sim4.case_mbam import (
    apply_case_timeline_to_npc_states,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def test_timeline_runtime_updates_availability_room_and_schedule() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    case_state = generate_case_state_for_seed_id("A")
    states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)

    at_2m, applied = apply_case_timeline_to_npc_states(
        case_state=case_state,
        npc_states=states,
        elapsed_seconds=120.0,
        applied_beat_ids=(),
    )
    assert at_2m["elodie"].availability == "busy"
    assert at_2m["elodie"].schedule_state.current_beat_id == "T_PLUS_02_CURATOR_CONTAINMENT"
    assert at_2m["elodie"].schedule_state.last_transition_at == "T+0120s"
    assert "T_PLUS_02_CURATOR_CONTAINMENT" in applied

    at_10m, applied = apply_case_timeline_to_npc_states(
        case_state=case_state,
        npc_states=at_2m,
        elapsed_seconds=600.0,
        applied_beat_ids=applied,
    )
    assert at_10m["laurent"].current_room_id == "PHONE_REMOTE"
    assert at_10m["laurent"].availability == "busy"
    assert at_10m["laurent"].schedule_state.current_beat_id == "T_PLUS_10_DONOR_EVENT"


def test_timeline_runtime_applies_archive_friction_to_marc() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    case_state = generate_case_state_for_seed_id("B")
    states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    base_trust = states["marc"].trust

    final_states, _applied = apply_case_timeline_to_npc_states(
        case_state=case_state,
        npc_states=states,
        elapsed_seconds=900.0,
        applied_beat_ids=(),
    )
    marc = final_states["marc"]
    assert marc.availability == "restricted"
    assert marc.emotion == "annoyed"
    assert marc.card_state.trust_trend == "down"
    assert marc.schedule_state.current_beat_id == "T_PLUS_15_TERMINAL_ARCHIVE"
    assert marc.trust <= base_trust


def test_timeline_runtime_is_deterministic_for_same_input() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    case_state = generate_case_state_for_seed_id("C")
    states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)

    first, applied_first = apply_case_timeline_to_npc_states(
        case_state=case_state,
        npc_states=states,
        elapsed_seconds=720.0,
        applied_beat_ids=(),
    )
    second, applied_second = apply_case_timeline_to_npc_states(
        case_state=case_state,
        npc_states=states,
        elapsed_seconds=720.0,
        applied_beat_ids=(),
    )

    assert first == second
    assert applied_first == applied_second
