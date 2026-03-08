from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
    InvestigationProgressState,
    action_flags_from_dialogue_turn,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    build_initial_mbam_object_state,
    build_visible_outcome_projection,
    build_debug_outcome_projection,
    build_dialogue_execution_context,
    evaluate_mbam_case_outcome,
    execute_dialogue_turn,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
)
from backend.sim4.case_mbam.dialogue_domain import DialogueTurnRequest, DialogueTurnSlotValue
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def _setup(seed: str):
    case_state = generate_case_state_for_seed_id(seed)
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    npc_states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    progress = build_initial_investigation_progress(case_state)
    object_state = build_initial_mbam_object_state(case_state)
    return case_state, npc_states, progress, object_state


def test_outcome_engine_starts_in_progress_and_deterministic() -> None:
    case_state, npc_states, progress, object_state = _setup("A")

    first = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        elapsed_seconds=0.0,
    )
    second = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        elapsed_seconds=0.0,
    )

    assert first == second
    assert first.primary_outcome == "in_progress"
    assert first.recovery_success.satisfied is False
    assert first.accusation_success.satisfied is False
    assert first.soft_fail.triggered is False
    assert first.best_outcome.satisfied is False
    assert first.contradiction_required_for_accusation is True


def test_outcome_engine_recovery_success_uses_case_rules_and_medallion_state() -> None:
    case_state, npc_states, progress, object_state = _setup("A")

    progress = InvestigationProgressState(
        discovered_evidence_ids=("E3_METHOD_TRACE",),
        collected_evidence_ids=("E3_METHOD_TRACE",),
        observed_clue_ids=progress.observed_clue_ids,
        known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union({"N8"}))),
        unlockable_contradiction_edge_ids=progress.unlockable_contradiction_edge_ids,
        known_contradiction_edge_ids=progress.known_contradiction_edge_ids,
        consumed_action_keys=progress.consumed_action_keys,
        satisfied_action_flags=progress.satisfied_action_flags,
    )
    object_state = replace(
        object_state,
        o2_medallion=replace(object_state.o2_medallion, status="recovered", location="player_inventory"),
    )

    result = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        elapsed_seconds=120.0,
    )

    assert result.recovery_success.satisfied is True
    assert result.primary_outcome == "recovery_success"
    assert result.medallion_status == "recovered"
    assert "action:recover_medallion" in result.action_flags


def test_outcome_engine_accusation_path_requires_contradiction_action() -> None:
    case_state, npc_states, progress, object_state = _setup("C")

    base_progress = InvestigationProgressState(
        discovered_evidence_ids=("E2_CAFE_RECEIPT",),
        collected_evidence_ids=("E2_CAFE_RECEIPT",),
        observed_clue_ids=progress.observed_clue_ids,
        known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union({"N3", "N4", "N5"}))),
        unlockable_contradiction_edge_ids=progress.unlockable_contradiction_edge_ids,
        known_contradiction_edge_ids=progress.known_contradiction_edge_ids,
        consumed_action_keys=progress.consumed_action_keys,
        satisfied_action_flags=("action:accuse_laurent",),
    )

    missing_contradiction = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=base_progress,
        object_state=object_state,
        npc_states=npc_states,
    )
    assert missing_contradiction.accusation_success.satisfied is False
    assert "action:state_contradiction_N3_N4" in missing_contradiction.accusation_success.missing_action_flags

    with_contradiction = replace(
        base_progress,
        satisfied_action_flags=("action:accuse_laurent", "action:state_contradiction_N3_N4"),
    )
    satisfied = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=with_contradiction,
        object_state=object_state,
        npc_states=npc_states,
    )
    assert satisfied.accusation_success.satisfied is True
    assert satisfied.contradiction_requirement_satisfied is True
    assert satisfied.primary_outcome == "accusation_success"


def test_outcome_engine_soft_fail_clock_trigger_is_enforced() -> None:
    case_state, npc_states, progress, object_state = _setup("B")

    result = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        elapsed_seconds=1200.0,
    )

    assert result.soft_fail.triggered is True
    assert "clock:post_T_PLUS_20_without_recovery" in result.soft_fail.matched_trigger_conditions
    assert result.primary_outcome == "soft_fail"


def test_outcome_engine_best_outcome_requires_full_rule_set_and_relationship_flags() -> None:
    case_state, npc_states, progress, object_state = _setup("B")

    progress = InvestigationProgressState(
        discovered_evidence_ids=("E2_CAFE_RECEIPT", "E3_METHOD_TRACE"),
        collected_evidence_ids=("E2_CAFE_RECEIPT", "E3_METHOD_TRACE"),
        observed_clue_ids=progress.observed_clue_ids,
        known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union({"N3", "N4", "N8"}))),
        unlockable_contradiction_edge_ids=progress.unlockable_contradiction_edge_ids,
        known_contradiction_edge_ids=progress.known_contradiction_edge_ids,
        consumed_action_keys=progress.consumed_action_keys,
        satisfied_action_flags=(
            "action:state_contradiction_N3_N4",
            "action:accuse_samira",
            "action:french_summary_x2",
            "action:polite_gate_usage",
        ),
    )
    object_state = replace(
        object_state,
        o2_medallion=replace(object_state.o2_medallion, status="recovered", location="player_inventory"),
    )

    result = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        relationship_flags=("rel_elodie_positive", "rel_marc_positive"),
    )
    assert result.best_outcome.satisfied is True
    assert result.primary_outcome == "best_outcome"

    escalated = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        relationship_flags=("rel_elodie_positive", "rel_marc_positive"),
        outcome_flags=("outcome:public_escalation",),
    )
    assert escalated.best_outcome.satisfied is False
    assert escalated.public_escalation is True


def test_dialogue_turn_action_flag_derivation_and_projection_shapes() -> None:
    case_state, npc_states, progress, _object_state = _setup("C")
    tuned_npc_states = dict(npc_states)
    tuned_npc_states["marc"] = replace(tuned_npc_states["marc"], trust=0.9)
    context = build_dialogue_execution_context(
        replace(progress, known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union({"N1"})))),
        tuned_npc_states,
        elapsed_seconds=720.0,
    )
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)

    request = DialogueTurnRequest(
        scene_id="S2",
        npc_id="marc",
        intent_id="request_access",
        provided_slots=(DialogueTurnSlotValue(slot_name="reason", value="verifier les logs"),),
    )
    result = execute_dialogue_turn(case_state, runtime, request, context=replace(context, elapsed_seconds=120.0))
    flags = action_flags_from_dialogue_turn(case_state, request, result, prior_summary_pass_count=1)
    assert "action:polite_gate_usage" in flags

    eval_result = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress,
        object_state=build_initial_mbam_object_state(case_state),
        npc_states=npc_states,
        extra_action_flags=flags,
    )
    visible = build_visible_outcome_projection(eval_result)
    debug = build_debug_outcome_projection(eval_result)

    assert set(visible.keys()) == {
        "truth_epoch",
        "primary_outcome",
        "terminal",
        "recovery_success",
        "accusation_success",
        "soft_fail",
        "best_outcome",
        "contradiction_required_for_accusation",
        "contradiction_requirement_satisfied",
        "quiet_recovery",
        "public_escalation",
        "soft_fail_latched",
        "best_outcome_awarded",
        "soft_fail_reasons",
        "continuity_flags",
    }
    assert debug["debug_scope"] == "outcome_state_private"
