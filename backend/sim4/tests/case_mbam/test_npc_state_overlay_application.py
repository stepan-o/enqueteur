from __future__ import annotations

from backend.sim4.case_mbam import (
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def test_seed_a_overlay_applies_ally_and_misdirector_profiles() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    case_state = generate_case_state_for_seed_id("A")

    states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)

    marc = states["marc"]
    assert marc.overlay_role_slot == "ALLY"
    assert marc.overlay_helpfulness == "high"
    assert "ally_knows_partial_path" in marc.known_fact_flags
    assert marc.soft_alignment_hint == "helping_quietly"
    assert marc.card_state.profile_id == "marc_a_ally"

    elodie = states["elodie"]
    assert elodie.overlay_role_slot == "MISDIRECTOR"
    assert elodie.overlay_helpfulness == "low"
    assert "pushes_safe_explanation" in elodie.belief_flags
    assert "time_fuzz_1" in elodie.misremember_flags
    assert elodie.soft_alignment_hint == "saving_face"
    assert elodie.card_state.profile_id == "elodie_a_misdirector"


def test_seed_b_and_c_overlay_assignments_differ_deterministically() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    states_b = initialize_mbam_npc_states_from_case_state(
        world_ctx,
        generate_case_state_for_seed_id("B"),
    )
    states_c = initialize_mbam_npc_states_from_case_state(
        world_ctx,
        generate_case_state_for_seed_id("C"),
    )

    assert states_b["samira"].overlay_role_slot == "CULPRIT"
    assert states_b["samira"].overlay_helpfulness == "low"
    assert "method_badge_borrow" in states_b["samira"].hidden_flags
    assert "drop_cafe_bathroom_stash" in states_b["samira"].hidden_flags
    assert states_b["samira"].soft_alignment_hint == "protecting_self"
    assert states_b["samira"].card_state.profile_id == "samira_b_culprit"

    assert states_c["laurent"].overlay_role_slot == "CULPRIT"
    assert states_c["laurent"].overlay_helpfulness == "low"
    assert "method_case_left_unlatched" in states_c["laurent"].hidden_flags
    assert "drop_coat_rack_pocket" in states_c["laurent"].hidden_flags
    assert states_c["laurent"].soft_alignment_hint == "protecting_self"
    assert states_c["laurent"].card_state.profile_id == "laurent_c_culprit"

    assert states_b["jo"].overlay_role_slot == "ALLY"
    assert states_c["elodie"].overlay_role_slot == "ALLY"


def test_overlay_application_is_reproducible_for_same_seed() -> None:
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    case_state = generate_case_state_for_seed_id("C")

    first = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    second = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    assert first == second
