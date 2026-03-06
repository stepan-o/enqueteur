from __future__ import annotations

import pytest

from backend.sim4.case_mbam import (
    build_initial_npc_state,
    initialize_mbam_npc_states,
    list_cast_ids,
    resolve_world_room_id,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def test_initialize_mbam_npc_states_creates_fixed_five_states() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    states = initialize_mbam_npc_states(world_ctx)

    assert tuple(states.keys()) == list_cast_ids()
    assert set(states.keys()) == {"elodie", "marc", "samira", "laurent", "jo"}


def test_initialize_mbam_npc_states_is_deterministic() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    first = initialize_mbam_npc_states(world_ctx)
    second = initialize_mbam_npc_states(world_ctx)
    assert first == second


def test_npc_state_defaults_include_required_runtime_fields() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    states = initialize_mbam_npc_states(world_ctx)

    for npc_id in list_cast_ids():
        state = states[npc_id]
        assert state.npc_id == npc_id
        assert state.overlay_role_slot != ""
        assert state.overlay_helpfulness == "medium"
        assert state.current_room_id != ""
        assert state.availability == "available"
        assert state.trust == 0.0
        assert state.stress == 0.0
        assert state.stance in {"helpful", "procedural", "evasive", "defensive", "manipulative", "flustered"}
        assert state.emotion in {"calm", "stressed", "amused", "annoyed", "nervous", "guarded"}
        assert state.soft_alignment_hint in {
            "protecting_institution",
            "protecting_self",
            "protecting_someone_else",
            "saving_face",
            "helping_quietly",
        }
        assert state.current_scene_id is None
        assert state.card_state.trust_trend == "flat"
        assert state.card_state.profile_id is None
        assert state.schedule_state.current_beat_id is None
        assert state.schedule_state.next_beat_id is not None
        assert state.schedule_state.last_transition_at is None


def test_npc_state_room_tokens_link_to_world_layout_ids() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    states = initialize_mbam_npc_states(world_ctx)

    for state in states.values():
        world_room_id = resolve_world_room_id(state.current_room_id)
        assert world_room_id in world_ctx.rooms_by_id


def test_build_initial_npc_state_for_one_actor_sets_card_and_schedule_defaults() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    state = build_initial_npc_state(npc_id="marc", world_ctx=world_ctx)
    assert state.npc_id == "marc"
    assert state.overlay_role_slot == "GUARD"
    assert state.overlay_helpfulness == "medium"
    assert state.current_room_id == "SECURITY_OFFICE"
    assert state.card_state.portrait_variant == "procedural"
    assert state.card_state.profile_id is None
    assert state.card_state.suggested_interaction_mode == "procedural"
    assert state.schedule_state.next_beat_id == "T_PLUS_05_GUARD_PATROL_SHIFT"


def test_initialize_mbam_npc_states_requires_mbam_rooms() -> None:
    world_ctx = WorldContext()
    with pytest.raises(ValueError):
        initialize_mbam_npc_states(world_ctx)
