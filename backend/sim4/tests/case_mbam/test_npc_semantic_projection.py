from __future__ import annotations

from backend.sim4.case_mbam import (
    build_debug_npc_semantic_projection,
    build_visible_npc_semantic_projection,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def test_visible_npc_semantic_projection_contains_safe_fields_only() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    states = initialize_mbam_npc_states_from_case_state(
        world_ctx,
        generate_case_state_for_seed_id("B"),
    )

    projection = build_visible_npc_semantic_projection(states)
    assert len(projection) == 5

    first = projection[0]
    assert set(first.keys()) == {
        "npc_id",
        "current_room_id",
        "availability",
        "trust",
        "stress",
        "stance",
        "emotion",
        "soft_alignment_hint",
        "visible_behavior_flags",
        "current_scene_id",
        "card_state",
    }
    assert "overlay_role_slot" not in first
    assert "known_fact_flags" not in first
    assert "hidden_flags" not in first
    assert "profile_id" not in first["card_state"]


def test_visible_projection_sanitizes_overlay_behavior_flags() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    states = initialize_mbam_npc_states_from_case_state(
        world_ctx,
        generate_case_state_for_seed_id("A"),
    )

    projection = build_visible_npc_semantic_projection(states)
    marc = next(entry for entry in projection if entry["npc_id"] == "marc")
    flags = marc["visible_behavior_flags"]
    assert all(not str(flag).startswith("overlay_role_") for flag in flags)
    assert all(not str(flag).startswith("overlay_helpfulness_") for flag in flags)


def test_debug_npc_semantic_projection_includes_private_overlay_truth() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    states = initialize_mbam_npc_states_from_case_state(
        world_ctx,
        generate_case_state_for_seed_id("C"),
    )

    projection = build_debug_npc_semantic_projection(states)
    laurent = next(entry for entry in projection if entry["npc_id"] == "laurent")
    assert laurent["overlay_role_slot"] == "CULPRIT"
    assert laurent["overlay_helpfulness"] == "low"
    assert "method_case_left_unlatched" in laurent["hidden_flags"]
    assert "drop_coat_rack_pocket" in laurent["hidden_flags"]
    assert "profile_id" in laurent["card_state"]
