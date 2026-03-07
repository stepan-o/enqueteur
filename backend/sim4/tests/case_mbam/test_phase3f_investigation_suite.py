from __future__ import annotations

from backend.sim4.case_mbam import (
    apply_execution_result_to_progress,
    build_debug_investigation_projection,
    build_initial_investigation_progress,
    build_initial_mbam_object_state,
    build_visible_investigation_projection,
    command_action_key,
    contradiction_requirement_satisfied_for_accusation,
    execute_contradiction_edge,
    execute_investigation_command,
    generate_case_state_for_seed_id,
    get_affordances_for_object,
    list_mbam_object_ids,
    make_investigation_command,
    validate_investigation_command,
)


def _initial(seed: str):
    case_state = generate_case_state_for_seed_id(seed)
    object_state = build_initial_mbam_object_state(case_state)
    progress = build_initial_investigation_progress(case_state)
    return case_state, object_state, progress


def _execute_and_apply(
    *,
    case_state,
    object_state,
    progress,
    object_id: str,
    affordance_id: str,
    prerequisites: tuple[str, ...] = (),
):
    execution = execute_investigation_command(
        make_investigation_command(object_id=object_id, affordance_id=affordance_id),
        case_state=case_state,
        object_state=object_state,
        available_prerequisites=prerequisites,
    )
    update = apply_execution_result_to_progress(case_state, progress, execution)
    return execution, update.progress_after


def _run_investigation_sequence(seed: str):
    case_state, object_state, progress = _initial(seed)

    for object_id, affordance_id, prerequisites in (
        ("O6_BADGE_TERMINAL", "request_access", ("scene:S2", "trust:marc>=gate")),
        ("O6_BADGE_TERMINAL", "view_logs", ("access:terminal_granted",)),
        ("O4_BENCH", "inspect", ()),
        ("O1_DISPLAY_CASE", "examine_surface", ()),
        ("O9_RECEIPT_PRINTER", "ask_for_receipt", ("scene:S4",)),
        ("O9_RECEIPT_PRINTER", "read_receipt", ("inventory:E2_CAFE_RECEIPT",)),
    ):
        execution, progress = _execute_and_apply(
            case_state=case_state,
            object_state=object_state,
            progress=progress,
            object_id=object_id,
            affordance_id=affordance_id,
            prerequisites=prerequisites,
        )
        object_state = execution.object_state_after

    visible_projection = build_visible_investigation_projection(
        case_state=case_state,
        object_state=object_state,
        progress=progress,
    )
    return case_state, object_state, progress, visible_projection


def test_phase3f_object_state_and_affordance_defaults_are_deterministic() -> None:
    expected_actions = {
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
    assert tuple(expected_actions.keys()) == list_mbam_object_ids()

    for object_id in list_mbam_object_ids():
        definitions = get_affordances_for_object(object_id)
        assert {row.affordance_id for row in definitions} == expected_actions[object_id]
        assert all(row.result_fields for row in definitions)

    state_a_1 = build_initial_mbam_object_state(generate_case_state_for_seed_id("A"))
    state_a_2 = build_initial_mbam_object_state(generate_case_state_for_seed_id("A"))
    assert state_a_1 == state_a_2


def test_phase3f_command_validation_paths_are_deterministic() -> None:
    case_state = generate_case_state_for_seed_id("B")
    object_state = build_initial_mbam_object_state(case_state)

    valid = validate_investigation_command(
        make_investigation_command(object_id="O3_WALL_LABEL", affordance_id="read"),
        object_state=object_state,
    )
    assert valid.kind == "success"
    assert valid.code == "validated"

    invalid = validate_investigation_command(
        make_investigation_command(object_id="O3_WALL_LABEL", affordance_id="request_access"),
        object_state=object_state,
    )
    assert invalid.kind == "invalid_action"
    assert invalid.code == "affordance_not_allowed_for_object"

    blocked = validate_investigation_command(
        make_investigation_command(object_id="O6_BADGE_TERMINAL", affordance_id="view_logs"),
        object_state=object_state,
        available_prerequisites=(),
    )
    assert blocked.kind == "blocked_prerequisite"
    assert blocked.code == "missing_prerequisites"
    assert blocked.missing_prerequisites == ("access:terminal_granted",)


def test_phase3f_repeat_state_dependent_and_consumed_paths_behave_as_expected() -> None:
    case_state, object_state, _progress = _initial("A")

    repeat_first = execute_investigation_command(
        make_investigation_command(object_id="O10_BULLETIN_BOARD", affordance_id="read"),
        case_state=case_state,
        object_state=object_state,
    )
    repeat_second = execute_investigation_command(
        make_investigation_command(object_id="O10_BULLETIN_BOARD", affordance_id="read"),
        case_state=case_state,
        object_state=repeat_first.object_state_after,
    )
    assert repeat_first.ack.kind == "success"
    assert repeat_second.ack.kind == "success"
    assert repeat_first.object_state_after == repeat_second.object_state_after

    bench_first = execute_investigation_command(
        make_investigation_command(object_id="O4_BENCH", affordance_id="inspect"),
        case_state=case_state,
        object_state=object_state,
    )
    bench_second = execute_investigation_command(
        make_investigation_command(object_id="O4_BENCH", affordance_id="inspect"),
        case_state=case_state,
        object_state=bench_first.object_state_after,
    )
    assert bench_first.ack.kind == "success"
    assert bench_second.ack.kind == "no_op"
    assert bench_second.ack.code == "state_no_effect"

    command = make_investigation_command(object_id="O1_DISPLAY_CASE", affordance_id="check_lock")
    consumed = validate_investigation_command(
        command,
        object_state=object_state,
        consumed_action_keys=(command_action_key(command),),
    )
    assert consumed.kind == "state_consumed"
    assert consumed.code == "action_state_already_consumed"


def test_phase3f_evidence_discovery_and_collection_do_not_duplicate() -> None:
    case_state, object_state, progress = _initial("A")

    bench_first, progress_after_first = _execute_and_apply(
        case_state=case_state,
        object_state=object_state,
        progress=progress,
        object_id="O4_BENCH",
        affordance_id="inspect",
    )
    assert "E1_TORN_NOTE" in progress_after_first.discovered_evidence_ids
    assert "E1_TORN_NOTE" in progress_after_first.collected_evidence_ids

    bench_second, progress_after_second = _execute_and_apply(
        case_state=case_state,
        object_state=bench_first.object_state_after,
        progress=progress_after_first,
        object_id="O4_BENCH",
        affordance_id="inspect",
    )
    assert bench_second.ack.kind == "no_op"
    assert progress_after_second.discovered_evidence_ids.count("E1_TORN_NOTE") == 1
    assert progress_after_second.collected_evidence_ids.count("E1_TORN_NOTE") == 1

    surface, progress_after_surface = _execute_and_apply(
        case_state=case_state,
        object_state=bench_second.object_state_after,
        progress=progress_after_second,
        object_id="O1_DISPLAY_CASE",
        affordance_id="examine_surface",
    )
    assert surface.ack.kind == "success"
    assert "E3_METHOD_TRACE" in progress_after_surface.discovered_evidence_ids
    assert "E3_METHOD_TRACE" not in progress_after_surface.collected_evidence_ids
    assert progress_after_surface.discovered_evidence_ids.count("E3_METHOD_TRACE") == 1


def test_phase3f_fact_unlocks_and_contradiction_require_required_ingredients() -> None:
    case_state, object_state, progress = _initial("B")

    req_access, progress = _execute_and_apply(
        case_state=case_state,
        object_state=object_state,
        progress=progress,
        object_id="O6_BADGE_TERMINAL",
        affordance_id="request_access",
        prerequisites=("scene:S2", "trust:marc>=gate"),
    )
    logs, progress = _execute_and_apply(
        case_state=case_state,
        object_state=req_access.object_state_after,
        progress=progress,
        object_id="O6_BADGE_TERMINAL",
        affordance_id="view_logs",
        prerequisites=("access:terminal_granted",),
    )
    assert logs.ack.kind == "success"
    assert "N3" in progress.known_fact_ids
    assert "E3" not in progress.unlockable_contradiction_edge_ids

    blocked_receipt = execute_investigation_command(
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="read_receipt"),
        case_state=case_state,
        object_state=logs.object_state_after,
        available_prerequisites=(),
    )
    assert blocked_receipt.ack.kind == "blocked_prerequisite"
    assert "N4" not in progress.known_fact_ids

    receipt, progress = _execute_and_apply(
        case_state=case_state,
        object_state=logs.object_state_after,
        progress=progress,
        object_id="O9_RECEIPT_PRINTER",
        affordance_id="read_receipt",
        prerequisites=("inventory:E2_CAFE_RECEIPT",),
    )
    assert receipt.ack.kind == "success"
    assert "N4" in progress.known_fact_ids
    assert "E3" in progress.unlockable_contradiction_edge_ids
    assert contradiction_requirement_satisfied_for_accusation(case_state, progress) is False

    contradiction = execute_contradiction_edge(case_state, progress, edge_id="E3")
    assert contradiction.status == "success"
    assert contradiction.code == "contradiction_recorded"
    assert contradiction_requirement_satisfied_for_accusation(case_state, contradiction.progress_after) is True


def test_phase3f_projection_visible_shape_is_structural_and_safe() -> None:
    case_state, object_state, progress, visible = _run_investigation_sequence("C")
    debug = build_debug_investigation_projection(
        case_state=case_state,
        object_state=object_state,
        progress=progress,
    )

    assert visible["truth_epoch"] == 1
    assert len(visible["objects"]) == 10
    assert set(visible["evidence"].keys()) == {"discovered_ids", "collected_ids", "observed_not_collected_ids"}
    assert set(visible["facts"].keys()) == {"known_fact_ids"}
    assert set(visible["contradictions"].keys()) == {
        "unlockable_edge_ids",
        "known_edge_ids",
        "required_for_accusation",
        "requirement_satisfied",
    }

    for row in visible["objects"]:
        assert set(row.keys()) == {"object_id", "affordances", "observed_affordances", "known_state"}

    # Hidden case truth should not leak to player-visible projection.
    assert "N8" not in visible["facts"]["known_fact_ids"]
    assert "location" not in next(
        row["known_state"] for row in visible["objects"] if row["object_id"] == "O2_MEDALLION"
    )

    # Debug projection still carries private state for replay/debug.
    assert debug["object_state"]["o2_medallion"]["location"] == "coat_rack_pocket"


def test_phase3f_same_seed_and_action_sequence_is_fully_deterministic() -> None:
    first = _run_investigation_sequence("B")
    second = _run_investigation_sequence("B")
    third = _run_investigation_sequence("A")

    assert first == second

    # Cross-seed still varies in meaningful investigation outputs.
    first_visible = first[3]
    third_visible = third[3]
    assert first_visible != third_visible
