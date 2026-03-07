from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
    build_initial_mbam_object_state,
    execute_investigation_command,
    generate_case_state_for_seed_id,
    make_investigation_command,
)


def _case_and_state(seed: str):
    case_state = generate_case_state_for_seed_id(seed)
    object_state = build_initial_mbam_object_state(case_state)
    return case_state, object_state


def test_o1_check_lock_executes_and_surfaces_fact_candidate() -> None:
    case_state, object_state = _case_and_state("A")
    result = execute_investigation_command(
        make_investigation_command(
            object_id="O1_DISPLAY_CASE",
            affordance_id="check_lock",
        ),
        case_state=case_state,
        object_state=object_state,
    )
    assert result.ack.kind == "success"
    assert result.execution_kind == "executed"
    assert result.object_state_after == object_state
    assert result.fact_unlock_candidates == ("N7",)
    assert ("locked", "locked") in result.descriptive_observation


def test_o2_examine_blocks_when_medallion_missing_without_leaking_drop_location() -> None:
    case_state, object_state = _case_and_state("B")
    result = execute_investigation_command(
        make_investigation_command(
            object_id="O2_MEDALLION",
            affordance_id="examine",
        ),
        case_state=case_state,
        object_state=object_state,
        # Simulate caller trying to force prereq presence.
        available_prerequisites=("require:medallion_present_or_recovered",),
    )
    assert result.ack.kind == "blocked_prerequisite"
    assert result.ack.code == "medallion_not_accessible"
    assert ("status", "missing") in result.descriptive_observation
    assert all(key != "location" for key, _ in result.descriptive_observation)


def test_o4_bench_inspect_reveals_seed_specific_evidence_and_consumes_item_state() -> None:
    case_a, state_a = _case_and_state("A")
    result_a = execute_investigation_command(
        make_investigation_command(
            object_id="O4_BENCH",
            affordance_id="inspect",
        ),
        case_state=case_a,
        object_state=state_a,
    )
    assert result_a.ack.kind == "success"
    assert result_a.revealed_evidence_ids == ("E1_TORN_NOTE",)
    assert result_a.object_state_after.o4_bench.under_bench_item is False
    assert any(t.field_path == "o4_bench.under_bench_item" for t in result_a.interaction_transitions)

    case_b, state_b = _case_and_state("B")
    result_b = execute_investigation_command(
        make_investigation_command(
            object_id="O4_BENCH",
            affordance_id="inspect",
        ),
        case_state=case_b,
        object_state=state_b,
    )
    assert result_b.ack.kind == "success"
    assert result_b.revealed_evidence_ids == ("E2_CAFE_RECEIPT",)


def test_o6_terminal_archive_friction_depends_on_timeline_and_override() -> None:
    case_state, object_state = _case_and_state("C")

    no_override = execute_investigation_command(
        make_investigation_command(
            object_id="O6_BADGE_TERMINAL",
            affordance_id="request_access",
        ),
        case_state=case_state,
        object_state=object_state,
        elapsed_seconds=900.0,
        available_prerequisites=("scene:S2", "trust:marc>=gate"),
    )
    assert no_override.ack.kind == "no_op"
    assert no_override.ack.code == "terminal_archived_access_friction"
    assert no_override.timeline_effects == ("T_PLUS_15_TERMINAL_ARCHIVE",)
    assert no_override.object_state_after.o6_badge_terminal.archived is True

    with_override = execute_investigation_command(
        make_investigation_command(
            object_id="O6_BADGE_TERMINAL",
            affordance_id="request_access",
        ),
        case_state=case_state,
        object_state=object_state,
        elapsed_seconds=900.0,
        available_prerequisites=("scene:S2", "trust:marc>=gate", "override:terminal_archive"),
    )
    assert with_override.ack.kind == "success"
    assert ("access_granted", True) in with_override.descriptive_observation


def test_o8_attempt_code_handles_wrong_and_correct_code_deterministically() -> None:
    case_state, object_state = _case_and_state("A")
    wrong = execute_investigation_command(
        make_investigation_command(
            object_id="O8_KEYPAD_DOOR",
            affordance_id="attempt_code",
            item_context_id="0000",
        ),
        case_state=case_state,
        object_state=object_state,
        available_prerequisites=("input:code_4_digit",),
    )
    assert wrong.ack.kind == "no_op"
    assert wrong.ack.code == "incorrect_code"
    assert wrong.object_state_after.o8_keypad_door.locked is True

    correct = execute_investigation_command(
        make_investigation_command(
            object_id="O8_KEYPAD_DOOR",
            affordance_id="attempt_code",
            item_context_id="1758",
        ),
        case_state=case_state,
        object_state=object_state,
        available_prerequisites=("input:code_4_digit",),
    )
    assert correct.ack.kind == "success"
    assert correct.object_state_after.o8_keypad_door.locked is False
    assert any(t.field_path == "o8_keypad_door.locked" for t in correct.interaction_transitions)


def test_o9_receipt_printer_ask_and_read_return_structured_outputs() -> None:
    case_state, object_state = _case_and_state("B")
    ask = execute_investigation_command(
        make_investigation_command(
            object_id="O9_RECEIPT_PRINTER",
            affordance_id="ask_for_receipt",
        ),
        case_state=case_state,
        object_state=object_state,
        available_prerequisites=("scene:S4",),
    )
    assert ask.ack.kind == "success"
    assert ask.revealed_evidence_ids == ("E2_CAFE_RECEIPT",)
    assert ask.object_state_after.o9_receipt_printer.recent_receipts == ()

    read = execute_investigation_command(
        make_investigation_command(
            object_id="O9_RECEIPT_PRINTER",
            affordance_id="read_receipt",
        ),
        case_state=case_state,
        object_state=ask.object_state_after,
        available_prerequisites=("inventory:E2_CAFE_RECEIPT",),
    )
    assert read.ack.kind == "success"
    assert read.fact_unlock_candidates == ("N4",)
    assert ("time", "17:52") in read.descriptive_observation


def test_validate_only_does_not_apply_interaction_transitions() -> None:
    case_state, object_state = _case_and_state("A")
    result = execute_investigation_command(
        make_investigation_command(
            object_id="O4_BENCH",
            affordance_id="inspect",
            execution_intent="validate_only",
        ),
        case_state=case_state,
        object_state=object_state,
    )
    assert result.execution_kind == "validated_only"
    assert result.interaction_transitions == ()
    assert result.object_state_after == object_state


def test_execution_is_deterministic_for_same_inputs() -> None:
    case_state, object_state = _case_and_state("C")
    cmd = make_investigation_command(
        object_id="O7_SECURITY_BINDER",
        affordance_id="read",
    )
    first = execute_investigation_command(
        cmd,
        case_state=case_state,
        object_state=object_state,
        elapsed_seconds=120.0,
    )
    second = execute_investigation_command(
        cmd,
        case_state=case_state,
        object_state=object_state,
        elapsed_seconds=120.0,
    )
    assert first == second


def test_all_o1_to_o10_affordances_have_execution_handlers() -> None:
    case_state, object_state = _case_and_state("A")
    commands = (
        make_investigation_command(object_id="O1_DISPLAY_CASE", affordance_id="inspect"),
        make_investigation_command(object_id="O1_DISPLAY_CASE", affordance_id="check_lock"),
        make_investigation_command(object_id="O1_DISPLAY_CASE", affordance_id="examine_surface"),
        make_investigation_command(object_id="O2_MEDALLION", affordance_id="examine"),
        make_investigation_command(object_id="O3_WALL_LABEL", affordance_id="read"),
        make_investigation_command(object_id="O4_BENCH", affordance_id="inspect"),
        make_investigation_command(object_id="O5_VISITOR_LOGBOOK", affordance_id="read"),
        make_investigation_command(object_id="O6_BADGE_TERMINAL", affordance_id="request_access"),
        make_investigation_command(object_id="O6_BADGE_TERMINAL", affordance_id="view_logs"),
        make_investigation_command(object_id="O7_SECURITY_BINDER", affordance_id="read"),
        make_investigation_command(object_id="O8_KEYPAD_DOOR", affordance_id="inspect"),
        make_investigation_command(object_id="O8_KEYPAD_DOOR", affordance_id="attempt_code"),
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="ask_for_receipt"),
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="read_receipt"),
        make_investigation_command(object_id="O10_BULLETIN_BOARD", affordance_id="read"),
    )
    prereq = {
        ("O6_BADGE_TERMINAL", "request_access"): ("scene:S2", "trust:marc>=gate"),
        ("O6_BADGE_TERMINAL", "view_logs"): ("access:terminal_granted",),
        ("O8_KEYPAD_DOOR", "attempt_code"): ("input:code_4_digit",),
        ("O9_RECEIPT_PRINTER", "ask_for_receipt"): ("scene:S4",),
        ("O9_RECEIPT_PRINTER", "read_receipt"): ("inventory:E2_CAFE_RECEIPT",),
    }

    for cmd in commands:
        current_state = object_state
        if cmd.object_id == "O4_BENCH":
            current_state = replace(object_state, o4_bench=replace(object_state.o4_bench, under_bench_item=False))
        result = execute_investigation_command(
            cmd,
            case_state=case_state,
            object_state=current_state,
            available_prerequisites=prereq.get((cmd.object_id, cmd.affordance_id), ()),
        )
        assert result.ack.code != "unsupported_affordance_handler"
