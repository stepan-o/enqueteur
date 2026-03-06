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
