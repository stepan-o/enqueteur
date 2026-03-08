from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
    InvestigationProgressState,
    apply_outcome_branch_transitions,
    attempt_accusation_completion,
    attempt_recovery_completion,
    build_dialogue_execution_context,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    build_initial_mbam_object_state,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def _setup(seed: str):
    case_state = generate_case_state_for_seed_id(seed)
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    npc_states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    progress = build_initial_investigation_progress(case_state)
    object_state = build_initial_mbam_object_state(case_state)
    context = build_dialogue_execution_context(progress, npc_states, elapsed_seconds=0.0)
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)
    return case_state, npc_states, progress, object_state, runtime


def _runtime_with_s5_available(runtime):
    completion = dict(runtime.scene_completion_states)
    completion["S5"] = "available"
    return replace(
        runtime,
        scene_completion_states=tuple((scene_id, completion[scene_id]) for scene_id, _state in runtime.scene_completion_states),
        surfaced_scene_ids=tuple(sorted(set(runtime.surfaced_scene_ids).union({"S5"}))),
    )


def _with_elodie_trust(npc_states, trust: float):
    updated = dict(npc_states)
    updated["elodie"] = replace(updated["elodie"], trust=trust)
    return updated


def test_recovery_flow_blocks_when_scene_or_trust_prereqs_missing() -> None:
    case_state, npc_states, progress, object_state, runtime = _setup("A")

    result = attempt_recovery_completion(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        dialogue_runtime_state=runtime,
        npc_states=npc_states,
        elapsed_seconds=300.0,
    )

    assert result.status == "blocked"
    assert result.code == "scene_or_trust_prerequisite_missing"
    assert "S5" in result.missing_scene_ids or "S5_TRUST_GATE" in result.missing_scene_ids


def test_recovery_flow_completes_when_evidence_fact_and_scene_checks_pass() -> None:
    case_state, npc_states, progress, object_state, runtime = _setup("A")

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
    runtime = _runtime_with_s5_available(runtime)
    npc_states = _with_elodie_trust(npc_states, 0.9)

    result = attempt_recovery_completion(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        dialogue_runtime_state=runtime,
        npc_states=npc_states,
        elapsed_seconds=600.0,
    )

    assert result.status == "completed"
    assert result.code == "recovery_success_completed"
    assert "action:recover_medallion" in result.applied_action_flags
    assert result.object_state_after is not None
    assert result.object_state_after.o2_medallion.status == "recovered"
    assert result.outcome_after.recovery_success.satisfied is True


def test_accusation_flow_blocks_without_contradiction_corroboration() -> None:
    case_state, npc_states, progress, object_state, runtime = _setup("C")

    progress = InvestigationProgressState(
        discovered_evidence_ids=("E2_CAFE_RECEIPT",),
        collected_evidence_ids=("E2_CAFE_RECEIPT",),
        observed_clue_ids=progress.observed_clue_ids,
        known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union({"N3", "N4", "N5"}))),
        unlockable_contradiction_edge_ids=progress.unlockable_contradiction_edge_ids,
        known_contradiction_edge_ids=progress.known_contradiction_edge_ids,
        consumed_action_keys=progress.consumed_action_keys,
        satisfied_action_flags=(),
    )
    runtime = _runtime_with_s5_available(runtime)
    npc_states = _with_elodie_trust(npc_states, 0.9)

    result = attempt_accusation_completion(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        dialogue_runtime_state=runtime,
        npc_states=npc_states,
        elapsed_seconds=780.0,
        accused_id="laurent",
    )

    assert result.status == "blocked"
    assert result.code == "accusation_prerequisites_missing"
    assert "action:state_contradiction_N3_N4" in result.missing_action_flags


def test_accusation_flow_completes_for_culprit_with_required_evidence_and_contradiction() -> None:
    case_state, npc_states, progress, object_state, runtime = _setup("C")

    progress = InvestigationProgressState(
        discovered_evidence_ids=("E2_CAFE_RECEIPT",),
        collected_evidence_ids=("E2_CAFE_RECEIPT",),
        observed_clue_ids=progress.observed_clue_ids,
        known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union({"N3", "N4", "N5"}))),
        unlockable_contradiction_edge_ids=progress.unlockable_contradiction_edge_ids,
        known_contradiction_edge_ids=progress.known_contradiction_edge_ids,
        consumed_action_keys=progress.consumed_action_keys,
        satisfied_action_flags=("action:state_contradiction_N3_N4",),
    )
    runtime = _runtime_with_s5_available(runtime)
    npc_states = _with_elodie_trust(npc_states, 0.9)

    result = attempt_accusation_completion(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        dialogue_runtime_state=runtime,
        npc_states=npc_states,
        elapsed_seconds=780.0,
        accused_id="laurent",
    )

    assert result.status == "completed"
    assert result.code == "accusation_success_completed"
    assert "action:accuse_laurent" in result.applied_action_flags
    assert result.outcome_after.accusation_success.satisfied is True


def test_wrong_accusation_path_resolves_to_soft_fail_branch() -> None:
    case_state, npc_states, progress, object_state, runtime = _setup("C")
    runtime = _runtime_with_s5_available(runtime)
    npc_states = _with_elodie_trust(npc_states, 0.9)

    result = attempt_accusation_completion(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        dialogue_runtime_state=runtime,
        npc_states=npc_states,
        elapsed_seconds=780.0,
        accused_id="samira",
        public=True,
    )

    assert result.status == "completed"
    assert result.code == "wrong_accusation_soft_fail"
    assert result.applied_action_flags == ("action:wrong_accusation",)
    assert result.outcome_after.soft_fail.triggered is True
    assert "outcome:public_escalation" in result.applied_outcome_flags


def test_outcome_branch_transition_latches_soft_fail_and_item_leaves_building() -> None:
    case_state, npc_states, progress, object_state, _runtime = _setup("A")
    progress = replace(progress, satisfied_action_flags=("action:wrong_accusation",))

    first = apply_outcome_branch_transitions(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        elapsed_seconds=780.0,
    )

    assert first.soft_fail_applied is True
    assert "outcome:soft_fail_latched" in first.outcome_flags_after
    assert "item_leaves_building" in first.outcome_flags_after
    assert "outcome:item_left_building" in first.outcome_flags_after
    assert "continuity:item_left_building" in first.continuity_flags
    assert "continuity:relationship_penalty" in first.continuity_flags
    assert first.object_state_after is not None
    assert first.object_state_after.o2_medallion.location == "unknown"
    assert first.object_state_after.o2_medallion.status == "missing"

    second = apply_outcome_branch_transitions(
        case_state=case_state,
        progress=first.progress_after,
        object_state=first.object_state_after,
        npc_states=npc_states,
        elapsed_seconds=780.0,
        outcome_flags=first.outcome_flags_after,
    )
    assert second.soft_fail_applied is False
    assert second.applied_outcome_flags == ()


def test_outcome_branch_transition_awards_best_outcome_continuity_flags() -> None:
    case_state, npc_states, progress, object_state, _runtime = _setup("B")
    progress = InvestigationProgressState(
        discovered_evidence_ids=("E2_CAFE_RECEIPT", "E3_METHOD_TRACE"),
        collected_evidence_ids=("E2_CAFE_RECEIPT", "E3_METHOD_TRACE"),
        observed_clue_ids=progress.observed_clue_ids,
        known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union({"N3", "N4", "N8"}))),
        unlockable_contradiction_edge_ids=progress.unlockable_contradiction_edge_ids,
        known_contradiction_edge_ids=progress.known_contradiction_edge_ids,
        consumed_action_keys=progress.consumed_action_keys,
        satisfied_action_flags=(
            "action:recover_medallion",
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

    transition = apply_outcome_branch_transitions(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        elapsed_seconds=840.0,
        relationship_flags=("rel_elodie_positive", "rel_marc_positive"),
    )

    assert transition.best_outcome_applied is True
    assert transition.outcome_after.best_outcome.satisfied is True
    assert "outcome:best_outcome_awarded" in transition.outcome_flags_after
    assert "continuity:quiet_recovery" in transition.continuity_flags
    assert "continuity:no_public_escalation" in transition.continuity_flags
    assert "continuity:strong_key_trust" in transition.continuity_flags
