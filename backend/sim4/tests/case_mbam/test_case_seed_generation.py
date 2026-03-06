from __future__ import annotations

from backend.sim4.case_mbam import (
    build_cast_overlay_for_seed,
    generate_case_state,
    generate_case_state_for_seed_id,
    get_seed_fixture,
    resolve_seed_id,
)


def test_seed_id_resolution_for_explicit_ids_is_stable() -> None:
    assert resolve_seed_id("A") == "A"
    assert resolve_seed_id("b") == "B"
    assert resolve_seed_id(" C ") == "C"


def test_seed_value_resolution_for_numeric_inputs_is_deterministic() -> None:
    # abs(n) % 3 over (A, B, C)
    assert resolve_seed_id(0) == "A"
    assert resolve_seed_id(1) == "B"
    assert resolve_seed_id(2) == "C"
    assert resolve_seed_id(3) == "A"
    assert resolve_seed_id(-4) == "B"


def test_seed_value_resolution_for_string_inputs_is_stable() -> None:
    s = "mbam-demo-seed-value"
    assert resolve_seed_id(s) == resolve_seed_id(s)
    assert resolve_seed_id(s) in {"A", "B", "C"}


def test_canonical_role_locks_for_a_b_c() -> None:
    case_a = generate_case_state_for_seed_id("A")
    assert case_a.roles_assignment.culprit == "outsider"
    assert case_a.roles_assignment.method == "delivery_cart_swap"
    assert case_a.roles_assignment.ally == "marc"

    case_b = generate_case_state_for_seed_id("B")
    assert case_b.roles_assignment.culprit == "samira"
    assert case_b.roles_assignment.method == "badge_borrow"
    assert case_b.roles_assignment.ally == "jo"

    case_c = generate_case_state_for_seed_id("C")
    assert case_c.roles_assignment.culprit == "laurent"
    assert case_c.roles_assignment.method == "case_left_unlatched"
    assert case_c.roles_assignment.ally == "elodie"


def test_drop_selection_is_stable_per_fixture() -> None:
    assert get_seed_fixture("A").drop == "corridor_bin"
    assert get_seed_fixture("B").drop == "cafe_bathroom_stash"
    assert get_seed_fixture("C").drop == "coat_rack_pocket"


def test_cast_overlay_reflects_generated_roles() -> None:
    overlay_a = build_cast_overlay_for_seed("A")
    assert overlay_a.outsider.role_slot == "CULPRIT"
    assert overlay_a.marc.role_slot == "ALLY"
    assert overlay_a.elodie.role_slot == "MISDIRECTOR"

    overlay_b = build_cast_overlay_for_seed("B")
    assert overlay_b.samira.role_slot == "CULPRIT"
    assert overlay_b.jo.role_slot == "ALLY"
    assert overlay_b.laurent.role_slot == "MISDIRECTOR"

    overlay_c = build_cast_overlay_for_seed("C")
    assert overlay_c.laurent.role_slot == "CULPRIT"
    assert overlay_c.elodie.role_slot == "ALLY"
    assert overlay_c.samira.role_slot == "MISDIRECTOR"


def test_same_seed_generation_is_reproducible() -> None:
    first = generate_case_state("B")
    second = generate_case_state("B")

    assert first == second
    assert first.seed == "B"
    assert first.roles_assignment == second.roles_assignment
    assert first.cast_overlay == second.cast_overlay


def test_seed_value_generation_does_not_use_ambient_randomness() -> None:
    # This should always normalize to the same canonical seed in this process
    # and across runs because resolve_seed_id is deterministic.
    first = generate_case_state("value-123")
    second = generate_case_state("value-123")
    assert first == second


def test_generation_marks_medallion_in_drop_location() -> None:
    case_state = generate_case_state("A")
    assert case_state.evidence_placement.drop_location.contains_medallion is True


def test_timeline_contains_locked_mbam_anchors() -> None:
    case_state = generate_case_state("A")
    anchors = [(b.time_offset_sec, b.beat_id) for b in case_state.timeline_schedule]
    assert anchors == [
        (0, "T_PLUS_00_ARRIVAL"),
        (120, "T_PLUS_02_CURATOR_CONTAINMENT"),
        (300, "T_PLUS_05_GUARD_PATROL_SHIFT"),
        (480, "T_PLUS_08_INTERN_MOVEMENT"),
        (600, "T_PLUS_10_DONOR_EVENT"),
        (720, "T_PLUS_12_BARISTA_WITNESS_WINDOW"),
        (900, "T_PLUS_15_TERMINAL_ARCHIVE"),
    ]


def test_truth_graph_contains_required_n1_to_n8_nodes() -> None:
    case_state = generate_case_state("B")
    node_ids = {n.fact_id for n in case_state.truth_graph.nodes}
    assert node_ids == {"N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8"}


def test_truth_graph_encodes_contradiction_path() -> None:
    case_state = generate_case_state("C")
    relations = {(e.from_fact_id, e.to_fact_id, e.relation) for e in case_state.truth_graph.edges}
    assert ("N3", "N4", "contradicts") in relations
    n8 = next(n for n in case_state.truth_graph.nodes if n.fact_id == "N8")
    assert "need:N3" in n8.unlock_conditions
    assert "need:N4" in n8.unlock_conditions
    assert "need:contradiction_time_path" in n8.unlock_conditions


def test_seed_evidence_placement_differs_deterministically() -> None:
    a = generate_case_state("A").evidence_placement
    b = generate_case_state("B").evidence_placement
    c = generate_case_state("C").evidence_placement

    assert a.display_case.latch_condition == "scratched"
    assert b.display_case.latch_condition == "intact"
    assert c.display_case.latch_condition == "loose"

    assert a.bench.contains == "torn_note_fragment"
    assert b.bench.contains == "receipt_fragment"
    assert c.bench.contains == "torn_note_fragment"

    assert a.cafe.receipt_id == "R-A-1752"
    assert b.cafe.receipt_id == "R-B-1752"
    assert c.cafe.receipt_id == "R-C-1752"


def test_hidden_visible_slices_preserve_fact_boundary() -> None:
    case_state = generate_case_state("A")
    assert case_state.visible_case_slice.starting_known_fact_ids == ("N1",)
    assert case_state.hidden_case_slice.private_fact_ids == ("N8", "R_CULPRIT", "R_METHOD", "R_DROP")
    assert "accusation_requires_contradiction_path" in case_state.hidden_case_slice.private_overlay_flags


def test_scene_gates_define_s1_to_s5_progression() -> None:
    a = generate_case_state("A")
    b = generate_case_state("B")

    # S1 open start
    assert a.scene_gates.S1.required_fact_ids == ()
    assert a.scene_gates.S1.required_items == ()

    # S2 security gate uses trust + archival window
    assert a.scene_gates.S2.required_fact_ids == ("N1",)
    assert a.scene_gates.S2.time_window == "T+00..T+15"
    assert a.scene_gates.S2.trust_threshold is not None
    # If guard is ally, S2 threshold is lower
    assert a.scene_gates.S2.trust_threshold < b.scene_gates.S2.trust_threshold

    # S5 confrontation requires contradiction-path facts and receipt evidence
    assert a.scene_gates.S5.required_fact_ids == ("N3", "N4", "N8")
    assert a.scene_gates.S5.required_items == ("E2_CAFE_RECEIPT",)


def test_resolution_rules_encode_success_and_soft_fail_paths() -> None:
    c = generate_case_state("C")

    # Recovery path
    assert c.resolution_rules.recovery_success.required_fact_ids == ("N8",)
    assert "action:recover_medallion" in c.resolution_rules.recovery_success.required_actions

    # Accusation path must include contradiction use
    assert "N3" in c.resolution_rules.accusation_success.required_fact_ids
    assert "N4" in c.resolution_rules.accusation_success.required_fact_ids
    assert "action:state_contradiction_N3_N4" in c.resolution_rules.accusation_success.required_actions
    assert "action:accuse_laurent" in c.resolution_rules.accusation_success.required_actions

    # Soft fail branch
    assert "action:wrong_accusation" in c.resolution_rules.soft_fail.trigger_conditions
    assert "item_leaves_building" in c.resolution_rules.soft_fail.outcome_flags

    # Best outcome overlays stricter requirements
    assert "action:french_summary_x2" in c.resolution_rules.best_outcome.required_actions
    assert "rel_elodie_positive" in c.resolution_rules.best_outcome.required_relationship_flags
