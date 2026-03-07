from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
    InvestigationCommand,
    build_initial_mbam_object_state,
    command_action_key,
    generate_case_state_for_seed_id,
    list_supported_command_forms,
    make_investigation_command,
    validate_investigation_command,
)


def _state_for_seed(seed: str):
    return build_initial_mbam_object_state(generate_case_state_for_seed_id(seed))


def test_supported_command_forms_match_mbam_o1_to_o10() -> None:
    forms = list_supported_command_forms()
    assert forms == (
        ("O1_DISPLAY_CASE", ("inspect", "check_lock", "examine_surface")),
        ("O2_MEDALLION", ("examine",)),
        ("O3_WALL_LABEL", ("read",)),
        ("O4_BENCH", ("inspect",)),
        ("O5_VISITOR_LOGBOOK", ("read",)),
        ("O6_BADGE_TERMINAL", ("request_access", "view_logs")),
        ("O7_SECURITY_BINDER", ("read",)),
        ("O8_KEYPAD_DOOR", ("inspect", "attempt_code")),
        ("O9_RECEIPT_PRINTER", ("ask_for_receipt", "read_receipt")),
        ("O10_BULLETIN_BOARD", ("read",)),
    )


def test_action_key_is_deterministic_and_includes_optional_context() -> None:
    command = make_investigation_command(
        object_id="O6_BADGE_TERMINAL",
        affordance_id="request_access",
        execution_intent="execute",
        item_context_id="ID_CARD",
        evidence_context_id="E3_METHOD_TRACE",
        npc_context_id="marc",
    )
    assert command_action_key(command) == (
        "O6_BADGE_TERMINAL|request_access|execute|ID_CARD|E3_METHOD_TRACE|marc"
    )


def test_validation_success_when_affordance_is_known_and_prereqs_met() -> None:
    command = make_investigation_command(
        object_id="O6_BADGE_TERMINAL",
        affordance_id="request_access",
    )
    ack = validate_investigation_command(
        command,
        object_state=_state_for_seed("A"),
        available_prerequisites=("scene:S2", "trust:marc>=gate"),
    )
    assert ack.kind == "success"
    assert ack.code == "validated"
    assert ack.expected_prerequisites == ("scene:S2", "trust:marc>=gate")
    assert ack.missing_prerequisites == ()
    assert ack.result_fields == ("access_granted", "terminal_online", "terminal_archived")
    assert ack.reveal_fact_ids == ("N2",)
    assert ack.accepted is True


def test_validation_rejects_unknown_object_and_affordance() -> None:
    unknown_object = InvestigationCommand(object_id="OX_UNKNOWN", affordance_id="inspect")
    ack_unknown_object = validate_investigation_command(
        unknown_object,
        object_state=_state_for_seed("A"),
    )
    assert ack_unknown_object.kind == "invalid_action"
    assert ack_unknown_object.code == "unknown_object_id"

    unknown_affordance = InvestigationCommand(object_id="O1_DISPLAY_CASE", affordance_id="hack")
    ack_unknown_affordance = validate_investigation_command(
        unknown_affordance,
        object_state=_state_for_seed("A"),
    )
    assert ack_unknown_affordance.kind == "invalid_action"
    assert ack_unknown_affordance.code == "unknown_affordance_id"


def test_validation_rejects_affordance_not_allowed_for_object() -> None:
    command = make_investigation_command(
        object_id="O1_DISPLAY_CASE",
        affordance_id="read_receipt",
    )
    ack = validate_investigation_command(
        command,
        object_state=_state_for_seed("A"),
    )
    assert ack.kind == "invalid_action"
    assert ack.code == "affordance_not_allowed_for_object"
    assert ack.accepted is False


def test_validation_blocks_on_missing_prerequisites() -> None:
    command = make_investigation_command(
        object_id="O6_BADGE_TERMINAL",
        affordance_id="view_logs",
    )
    ack = validate_investigation_command(
        command,
        object_state=_state_for_seed("A"),
        available_prerequisites=(),
    )
    assert ack.kind == "blocked_prerequisite"
    assert ack.code == "missing_prerequisites"
    assert ack.missing_prerequisites == ("access:terminal_granted",)
    assert ack.result_fields == ("log_entries", "important_time")


def test_validation_returns_state_consumed_when_action_key_already_consumed() -> None:
    command = make_investigation_command(
        object_id="O1_DISPLAY_CASE",
        affordance_id="check_lock",
    )
    action_key = command_action_key(command)
    ack = validate_investigation_command(
        command,
        object_state=_state_for_seed("B"),
        consumed_action_keys=(action_key,),
    )
    assert ack.kind == "state_consumed"
    assert ack.code == "action_state_already_consumed"
    assert ack.accepted is False


def test_validation_returns_noop_for_state_with_no_effect() -> None:
    state = _state_for_seed("A")
    state = replace(
        state,
        o4_bench=replace(state.o4_bench, under_bench_item=False),
    )
    command = make_investigation_command(
        object_id="O4_BENCH",
        affordance_id="inspect",
    )
    ack = validate_investigation_command(
        command,
        object_state=state,
    )
    assert ack.kind == "no_op"
    assert ack.code == "state_no_effect"
    assert ack.accepted is True


def test_validation_is_deterministic_for_same_inputs() -> None:
    state = _state_for_seed("C")
    command = make_investigation_command(
        object_id="O9_RECEIPT_PRINTER",
        affordance_id="read_receipt",
        execution_intent="validate_only",
    )
    available = ("inventory:E2_CAFE_RECEIPT",)

    first = validate_investigation_command(
        command,
        object_state=state,
        available_prerequisites=available,
    )
    second = validate_investigation_command(
        command,
        object_state=state,
        available_prerequisites=available,
    )

    assert first == second
