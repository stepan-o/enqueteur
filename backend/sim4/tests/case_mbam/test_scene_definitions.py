from __future__ import annotations

from backend.sim4.case_mbam import (
    build_mbam_scene_definitions,
    generate_case_state_for_seed_id,
    get_mbam_scene_definition,
    list_mbam_scene_definitions,
)


def test_scene_definitions_cover_locked_s1_to_s5() -> None:
    case_state = generate_case_state_for_seed_id("A")
    scene_defs = build_mbam_scene_definitions(case_state)

    rows = list_mbam_scene_definitions(scene_defs)
    assert tuple(row.scene_id for row in rows) == ("S1", "S2", "S3", "S4", "S5")
    assert scene_defs.S1.primary_npc_id == "elodie"
    assert scene_defs.S2.primary_npc_id == "marc"
    assert scene_defs.S4.primary_npc_id == "jo"
    assert scene_defs.S5.primary_npc_id == "elodie"


def test_scene_definitions_align_with_case_state_scene_gates() -> None:
    case_state = generate_case_state_for_seed_id("C")
    scene_defs = build_mbam_scene_definitions(case_state)

    s1 = get_mbam_scene_definition(scene_defs, "S1")
    s2 = get_mbam_scene_definition(scene_defs, "S2")
    s3 = get_mbam_scene_definition(scene_defs, "S3")
    s4 = get_mbam_scene_definition(scene_defs, "S4")
    s5 = get_mbam_scene_definition(scene_defs, "S5")

    assert s1.case_gate == case_state.scene_gates.S1
    assert s2.case_gate == case_state.scene_gates.S2
    assert s3.case_gate == case_state.scene_gates.S3
    assert s4.case_gate == case_state.scene_gates.S4
    assert s5.case_gate == case_state.scene_gates.S5

    assert s2.scene_state.trust_gate.minimum_value == case_state.scene_gates.S2.trust_threshold
    assert s5.scene_state.trust_gate.minimum_value == case_state.scene_gates.S5.trust_threshold

    assert "N1" in s2.scene_state.allowed_fact_ids
    assert "N2" in s3.scene_state.allowed_fact_ids
    assert "N1" in s4.scene_state.allowed_fact_ids
    assert all(fact in s5.scene_state.allowed_fact_ids for fact in ("N3", "N4", "N8"))


def test_scene_definition_initial_states_follow_gate_accessibility_from_visible_start() -> None:
    case_state = generate_case_state_for_seed_id("B")
    scene_defs = build_mbam_scene_definitions(case_state)

    assert scene_defs.S1.progression.initial_state == "available"
    assert scene_defs.S2.progression.initial_state == "available"
    assert scene_defs.S3.progression.initial_state == "locked"
    assert scene_defs.S4.progression.initial_state == "available"
    assert scene_defs.S5.progression.initial_state == "locked"

    assert scene_defs.S1.progression.success_state == "completed"
    assert scene_defs.S1.progression.soft_failure_state == "failed_soft"


def test_scene_definition_core_intent_and_slot_contracts_match_scene_goals() -> None:
    case_state = generate_case_state_for_seed_id("A")
    scene_defs = build_mbam_scene_definitions(case_state)

    assert "request_permission" in scene_defs.S1.scene_state.allowed_intents
    assert "request_access" in scene_defs.S2.scene_state.allowed_intents
    assert "ask_when" in scene_defs.S3.scene_state.allowed_intents
    assert "ask_what_seen" in scene_defs.S4.scene_state.allowed_intents
    assert "accuse" in scene_defs.S5.scene_state.allowed_intents

    assert scene_defs.S3.scene_state.required_slots[0].slot_name == "time"
    assert tuple(slot.slot_name for slot in scene_defs.S5.scene_state.required_slots) == ("person", "reason")
    assert scene_defs.S5.scene_state.summary_requirement.min_fact_count == 2

    assert "scene:S1:inspection_permission" in scene_defs.S1.scene_state.unlock_outputs.scene_completion_flags
    assert "O6_BADGE_TERMINAL.request_access" in scene_defs.S2.scene_state.unlock_outputs.new_object_actions
    assert "scene:S3:timeline_sequence_built" in scene_defs.S3.scene_state.unlock_outputs.scene_completion_flags
    assert "O9_RECEIPT_PRINTER.read_receipt" in scene_defs.S4.scene_state.unlock_outputs.new_object_actions
    assert "scene:S5:confrontation_resolution" in scene_defs.S5.scene_state.unlock_outputs.scene_completion_flags


def test_scene_definition_s3_witness_actor_has_seeded_equivalent_when_samira_is_culprit() -> None:
    a = build_mbam_scene_definitions(generate_case_state_for_seed_id("A"))
    b = build_mbam_scene_definitions(generate_case_state_for_seed_id("B"))
    c = build_mbam_scene_definitions(generate_case_state_for_seed_id("C"))

    assert a.S3.primary_npc_id == "samira"
    assert b.S3.primary_npc_id == "elodie"  # Samira culprit fallback
    assert c.S3.primary_npc_id == "samira"


def test_scene_definitions_are_deterministic_for_same_seed() -> None:
    case_state = generate_case_state_for_seed_id("C")
    first = build_mbam_scene_definitions(case_state)
    second = build_mbam_scene_definitions(case_state)
    assert first == second
