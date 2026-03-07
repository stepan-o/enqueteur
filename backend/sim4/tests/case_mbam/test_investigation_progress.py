from __future__ import annotations

from backend.sim4.case_mbam import (
    apply_execution_result_to_progress,
    build_initial_mbam_object_state,
    build_initial_investigation_progress,
    contradiction_required_for_accusation,
    contradiction_requirement_satisfied_for_accusation,
    execute_contradiction_edge,
    execute_investigation_command,
    generate_case_state_for_seed_id,
    make_investigation_command,
)


def _state(seed: str):
    case_state = generate_case_state_for_seed_id(seed)
    object_state = build_initial_mbam_object_state(case_state)
    progress = build_initial_investigation_progress(case_state)
    return case_state, object_state, progress


def test_initial_progress_starts_with_visible_known_facts_only() -> None:
    case_state, _object_state, progress = _state("A")
    assert progress.known_fact_ids == case_state.visible_case_slice.starting_known_fact_ids
    assert progress.discovered_evidence_ids == ()
    assert progress.collected_evidence_ids == ()
    assert progress.known_contradiction_edge_ids == ()
    assert contradiction_required_for_accusation(case_state) is True
    assert contradiction_requirement_satisfied_for_accusation(case_state, progress) is False


def test_bench_execution_discovers_and_collects_evidence_then_unlocks_n6() -> None:
    case_state, object_state, progress = _state("A")
    execution = execute_investigation_command(
        make_investigation_command(object_id="O4_BENCH", affordance_id="inspect"),
        case_state=case_state,
        object_state=object_state,
    )
    update = apply_execution_result_to_progress(case_state, progress, execution)
    after = update.progress_after

    assert "E1_TORN_NOTE" in after.discovered_evidence_ids
    assert "E1_TORN_NOTE" in after.collected_evidence_ids
    assert "N6" in after.known_fact_ids
    assert "obs:O4_BENCH:inspect" in after.observed_clue_ids


def test_method_trace_is_observed_but_not_collected_and_still_unlocks_n7() -> None:
    case_state, object_state, progress = _state("C")
    execution = execute_investigation_command(
        make_investigation_command(object_id="O1_DISPLAY_CASE", affordance_id="examine_surface"),
        case_state=case_state,
        object_state=object_state,
    )
    update = apply_execution_result_to_progress(case_state, progress, execution)
    after = update.progress_after

    assert "E3_METHOD_TRACE" in after.discovered_evidence_ids
    assert "E3_METHOD_TRACE" not in after.collected_evidence_ids
    assert "clue:evidence:E3_METHOD_TRACE:observed_not_collected" in after.observed_clue_ids
    assert "N7" in after.known_fact_ids


def test_n3_plus_n4_unlocks_contradiction_edge_e3() -> None:
    case_state, object_state, progress = _state("B")

    req_access = execute_investigation_command(
        make_investigation_command(object_id="O6_BADGE_TERMINAL", affordance_id="request_access"),
        case_state=case_state,
        object_state=object_state,
        available_prerequisites=("scene:S2", "trust:marc>=gate"),
    )
    p1 = apply_execution_result_to_progress(case_state, progress, req_access).progress_after

    view_logs = execute_investigation_command(
        make_investigation_command(object_id="O6_BADGE_TERMINAL", affordance_id="view_logs"),
        case_state=case_state,
        object_state=req_access.object_state_after,
        available_prerequisites=("access:terminal_granted",),
    )
    p2 = apply_execution_result_to_progress(case_state, p1, view_logs).progress_after
    assert "N3" in p2.known_fact_ids

    read_receipt = execute_investigation_command(
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="read_receipt"),
        case_state=case_state,
        object_state=req_access.object_state_after,
        available_prerequisites=("inventory:E2_CAFE_RECEIPT",),
    )
    update = apply_execution_result_to_progress(case_state, p2, read_receipt)
    after = update.progress_after

    assert "N4" in after.known_fact_ids
    assert "E3" in after.unlockable_contradiction_edge_ids
    assert "E3" in update.newly_unlockable_contradiction_edge_ids


def test_execute_contradiction_edge_records_action_flag_for_accusation_path() -> None:
    case_state, object_state, progress = _state("A")

    view_logs = execute_investigation_command(
        make_investigation_command(object_id="O6_BADGE_TERMINAL", affordance_id="view_logs"),
        case_state=case_state,
        object_state=object_state,
        available_prerequisites=("access:terminal_granted",),
    )
    p1 = apply_execution_result_to_progress(case_state, progress, view_logs).progress_after
    read_receipt = execute_investigation_command(
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="read_receipt"),
        case_state=case_state,
        object_state=object_state,
        available_prerequisites=("inventory:E2_CAFE_RECEIPT",),
    )
    p2 = apply_execution_result_to_progress(case_state, p1, read_receipt).progress_after
    assert "E3" in p2.unlockable_contradiction_edge_ids

    contradiction = execute_contradiction_edge(case_state, p2, edge_id="E3")
    assert contradiction.status == "success"
    assert contradiction.code == "contradiction_recorded"
    assert contradiction.action_flag == "action:state_contradiction_N3_N4"
    after = contradiction.progress_after
    assert "E3" in after.known_contradiction_edge_ids
    assert contradiction_requirement_satisfied_for_accusation(case_state, after) is True


def test_contradiction_execution_blocks_when_facts_missing() -> None:
    case_state, _object_state, progress = _state("C")
    result = execute_contradiction_edge(case_state, progress, edge_id="E3")
    assert result.status == "blocked"
    assert result.code == "missing_required_facts"
    assert set(result.missing_fact_ids) == {"N3", "N4"}


def test_progress_updates_are_deterministic_for_same_inputs() -> None:
    case_state, object_state, progress = _state("B")
    execution = execute_investigation_command(
        make_investigation_command(object_id="O10_BULLETIN_BOARD", affordance_id="read"),
        case_state=case_state,
        object_state=object_state,
    )

    first = apply_execution_result_to_progress(case_state, progress, execution)
    second = apply_execution_result_to_progress(case_state, progress, execution)
    assert first == second
