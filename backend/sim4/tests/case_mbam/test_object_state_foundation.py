from __future__ import annotations

from backend.sim4.case_mbam import (
    build_initial_mbam_object_state,
    generate_case_state_for_seed_id,
    get_affordances_for_object,
    get_all_object_world_bindings,
    get_object_state_by_id,
    list_affordances,
    list_mbam_object_ids,
)


def test_object_registry_contains_locked_o1_to_o10_in_order() -> None:
    assert list_mbam_object_ids() == (
        "O1_DISPLAY_CASE",
        "O2_MEDALLION",
        "O3_WALL_LABEL",
        "O4_BENCH",
        "O5_VISITOR_LOGBOOK",
        "O6_BADGE_TERMINAL",
        "O7_SECURITY_BINDER",
        "O8_KEYPAD_DOOR",
        "O9_RECEIPT_PRINTER",
        "O10_BULLETIN_BOARD",
    )


def test_world_bindings_keep_case_vs_world_boundary_explicit() -> None:
    bindings = get_all_object_world_bindings()

    assert bindings["O1_DISPLAY_CASE"].world_object_id == 3002
    assert bindings["O6_BADGE_TERMINAL"].world_object_id == 3004
    assert bindings["O9_RECEIPT_PRINTER"].world_object_id == 3007
    assert bindings["O10_BULLETIN_BOARD"].world_object_id == 3008

    # Investigation objects may exist without static world object ids.
    assert bindings["O2_MEDALLION"].world_object_id is None
    assert bindings["O3_WALL_LABEL"].world_object_id is None
    assert bindings["O5_VISITOR_LOGBOOK"].world_object_id is None
    assert bindings["O7_SECURITY_BINDER"].world_object_id is None

    # O8 maps to a world door gate instead of a world object record.
    assert bindings["O8_KEYPAD_DOOR"].world_object_id is None
    assert bindings["O8_KEYPAD_DOOR"].world_door_id == 1002


def test_each_object_has_affordances_and_expected_actions() -> None:
    expected = {
        "O1_DISPLAY_CASE": {"inspect", "check_lock", "examine_surface"},
        "O2_MEDALLION": {"examine"},
        "O3_WALL_LABEL": {"read"},
        "O4_BENCH": {"inspect"},
        "O5_VISITOR_LOGBOOK": {"read"},
        "O6_BADGE_TERMINAL": {"request_access", "view_logs"},
        "O7_SECURITY_BINDER": {"read"},
        "O8_KEYPAD_DOOR": {"inspect", "attempt_code"},
        "O9_RECEIPT_PRINTER": {"ask_for_receipt", "read_receipt"},
        "O10_BULLETIN_BOARD": {"read"},
    }
    affordances = list_affordances()

    for object_id in list_mbam_object_ids():
        object_actions = {a.affordance_id for a in get_affordances_for_object(object_id)}
        assert object_actions == expected[object_id]

    assert len(affordances) == sum(len(v) for v in expected.values())


def test_affordance_reveal_contracts_are_explicit() -> None:
    by_key = {(a.object_id, a.affordance_id): a for a in list_affordances()}

    assert by_key[("O1_DISPLAY_CASE", "check_lock")].reveal_fact_ids == ("N7",)
    assert by_key[("O6_BADGE_TERMINAL", "request_access")].reveal_fact_ids == ("N2",)
    assert by_key[("O6_BADGE_TERMINAL", "view_logs")].reveal_fact_ids == ("N3",)
    assert by_key[("O9_RECEIPT_PRINTER", "read_receipt")].reveal_fact_ids == ("N4",)

    assert by_key[("O4_BENCH", "inspect")].reveal_evidence_ids == ("E1_TORN_NOTE",)
    assert by_key[("O9_RECEIPT_PRINTER", "ask_for_receipt")].reveal_evidence_ids == ("E2_CAFE_RECEIPT",)
    assert by_key[("O1_DISPLAY_CASE", "examine_surface")].reveal_evidence_ids == ("E3_METHOD_TRACE",)


def test_initial_object_state_is_seed_deterministic_and_varies_by_seed() -> None:
    state_a_1 = build_initial_mbam_object_state(generate_case_state_for_seed_id("A"))
    state_a_2 = build_initial_mbam_object_state(generate_case_state_for_seed_id("A"))
    state_b = build_initial_mbam_object_state(generate_case_state_for_seed_id("B"))
    state_c = build_initial_mbam_object_state(generate_case_state_for_seed_id("C"))

    assert state_a_1 == state_a_2

    # Method-driven display-case lock difference.
    assert state_a_1.o1_display_case.locked == "locked"
    assert state_c.o1_display_case.locked == "unlocked"

    # Seed-driven drop and receipt differences.
    assert state_a_1.o2_medallion.location == "corridor_bin"
    assert state_b.o2_medallion.location == "cafe_bathroom_stash"
    assert state_c.o2_medallion.location == "coat_rack_pocket"
    assert state_a_1.o9_receipt_printer.recent_receipts[0].receipt_id == "R-A-1752"
    assert state_b.o9_receipt_printer.recent_receipts[0].receipt_id == "R-B-1752"
    assert state_c.o9_receipt_printer.recent_receipts[0].receipt_id == "R-C-1752"


def test_object_bundle_can_be_addressed_by_o_id() -> None:
    state = build_initial_mbam_object_state(generate_case_state_for_seed_id("B"))
    for object_id in list_mbam_object_ids():
        assert get_object_state_by_id(state, object_id) is not None
