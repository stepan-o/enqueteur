from __future__ import annotations

"""Deterministic MBAM case completion flow (Phase 7B).

This module provides canonical backend completion attempts for:
- item recovery path
- accusation/reasoning path

It remains MBAM-specific and case-truth-driven.
"""

from dataclasses import dataclass
from dataclasses import replace
from typing import Iterable, Literal, Mapping, cast

from .cast_registry import FixedCastId
from .dialogue_runtime import DialogueSceneRuntimeState
from .investigation_progress import InvestigationProgressState
from .models import CaseState, CulpritId, ResolutionRequirement
from .npc_state import NPCState
from .object_state import MbamObjectStateBundle
from .outcome_engine import MbamOutcomeEvaluationResult, evaluate_mbam_case_outcome


CaseCompletionPath = Literal["recovery", "accusation"]
CaseCompletionStatus = Literal["completed", "blocked", "invalid"]


def _sorted_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({v for v in values if isinstance(v, str) and v}))


def _is_valid_culprit_id(value: str) -> bool:
    return value in {"samira", "laurent", "outsider"}


def _with_added_action_flags(
    progress: InvestigationProgressState,
    action_flags: Iterable[str],
) -> InvestigationProgressState:
    merged = tuple(sorted(set(progress.satisfied_action_flags).union(_sorted_unique(action_flags))))
    return replace(progress, satisfied_action_flags=merged)


def _scene_prereq_for_confrontation(
    case_state: CaseState,
    runtime_state: DialogueSceneRuntimeState | None,
    npc_states: Mapping[FixedCastId, NPCState] | None,
) -> tuple[tuple[str, ...], float | None, float | None]:
    missing_scene_ids: tuple[str, ...] = ()
    if runtime_state is not None:
        completion = dict(runtime_state.scene_completion_states)
        s5_state = completion.get("S5", "locked")
        surfaced = "S5" in runtime_state.surfaced_scene_ids
        if not surfaced and s5_state not in {"available", "in_progress", "completed"}:
            missing_scene_ids = ("S5",)

    trust_threshold = case_state.scene_gates.S5.trust_threshold
    trust_value: float | None = None
    if trust_threshold is not None and npc_states is not None:
        elodie = npc_states.get("elodie")
        trust_value = elodie.trust if elodie is not None else None
        if trust_value is None or trust_value < trust_threshold:
            missing_scene_ids = tuple(sorted(set(missing_scene_ids).union({"S5_TRUST_GATE"})))

    return missing_scene_ids, trust_threshold, trust_value


def _missing_requirement_parts(
    requirement: ResolutionRequirement,
    *,
    known_facts: set[str],
    known_items: set[str],
    known_actions: set[str],
    ignore_actions: Iterable[str] = (),
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    ignore = set(_sorted_unique(ignore_actions))
    missing_facts = tuple(sorted(fact for fact in requirement.required_fact_ids if fact not in known_facts))
    missing_items = tuple(sorted(item for item in requirement.required_items if item not in known_items))
    missing_actions = tuple(
        sorted(action for action in requirement.required_actions if action not in known_actions and action not in ignore)
    )
    return missing_facts, missing_items, missing_actions


@dataclass(frozen=True)
class CaseCompletionAttemptResult:
    path: CaseCompletionPath
    status: CaseCompletionStatus
    code: str
    accused_id: CulpritId | None
    missing_scene_ids: tuple[str, ...]
    trust_threshold: float | None
    trust_value: float | None
    missing_fact_ids: tuple[str, ...]
    missing_item_ids: tuple[str, ...]
    missing_action_flags: tuple[str, ...]
    applied_action_flags: tuple[str, ...]
    applied_outcome_flags: tuple[str, ...]
    progress_before: InvestigationProgressState
    progress_after: InvestigationProgressState
    object_state_before: MbamObjectStateBundle | None
    object_state_after: MbamObjectStateBundle | None
    outcome_before: MbamOutcomeEvaluationResult
    outcome_after: MbamOutcomeEvaluationResult


@dataclass(frozen=True)
class OutcomeBranchTransitionResult:
    progress_before: InvestigationProgressState
    progress_after: InvestigationProgressState
    object_state_before: MbamObjectStateBundle | None
    object_state_after: MbamObjectStateBundle | None
    outcome_flags_before: tuple[str, ...]
    outcome_flags_after: tuple[str, ...]
    continuity_flags: tuple[str, ...]
    applied_outcome_flags: tuple[str, ...]
    soft_fail_applied: bool
    best_outcome_applied: bool
    outcome_before: MbamOutcomeEvaluationResult
    outcome_after: MbamOutcomeEvaluationResult


def attempt_recovery_completion(
    *,
    case_state: CaseState,
    progress: InvestigationProgressState,
    object_state: MbamObjectStateBundle,
    dialogue_runtime_state: DialogueSceneRuntimeState | None,
    npc_states: Mapping[FixedCastId, NPCState] | None,
    elapsed_seconds: float,
    extra_action_flags: Iterable[str] = (),
    relationship_flags: Iterable[str] = (),
    outcome_flags: Iterable[str] = (),
    quiet: bool = True,
) -> CaseCompletionAttemptResult:
    outcome_before = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        elapsed_seconds=elapsed_seconds,
        extra_action_flags=extra_action_flags,
        relationship_flags=relationship_flags,
        outcome_flags=outcome_flags,
    )

    missing_scene_ids, trust_threshold, trust_value = _scene_prereq_for_confrontation(
        case_state,
        dialogue_runtime_state,
        npc_states,
    )
    if missing_scene_ids:
        return CaseCompletionAttemptResult(
            path="recovery",
            status="blocked",
            code="scene_or_trust_prerequisite_missing",
            accused_id=None,
            missing_scene_ids=missing_scene_ids,
            trust_threshold=trust_threshold,
            trust_value=trust_value,
            missing_fact_ids=(),
            missing_item_ids=(),
            missing_action_flags=(),
            applied_action_flags=(),
            applied_outcome_flags=(),
            progress_before=progress,
            progress_after=progress,
            object_state_before=object_state,
            object_state_after=object_state,
            outcome_before=outcome_before,
            outcome_after=outcome_before,
        )

    known_facts = set(progress.known_fact_ids)
    known_items = set(progress.discovered_evidence_ids).union(progress.collected_evidence_ids)
    known_actions = set(progress.satisfied_action_flags).union(_sorted_unique(extra_action_flags))

    missing_facts, missing_items, missing_actions = _missing_requirement_parts(
        case_state.resolution_rules.recovery_success,
        known_facts=known_facts,
        known_items=known_items,
        known_actions=known_actions,
        ignore_actions=("action:recover_medallion",),
    )
    if missing_facts or missing_items or missing_actions:
        return CaseCompletionAttemptResult(
            path="recovery",
            status="blocked",
            code="recovery_prerequisites_missing",
            accused_id=None,
            missing_scene_ids=(),
            trust_threshold=trust_threshold,
            trust_value=trust_value,
            missing_fact_ids=missing_facts,
            missing_item_ids=missing_items,
            missing_action_flags=missing_actions,
            applied_action_flags=(),
            applied_outcome_flags=(),
            progress_before=progress,
            progress_after=progress,
            object_state_before=object_state,
            object_state_after=object_state,
            outcome_before=outcome_before,
            outcome_after=outcome_before,
        )

    applied_actions: tuple[str, ...] = ()
    progress_after = progress
    object_after = object_state

    if object_state.o2_medallion.status != "recovered":
        progress_after = _with_added_action_flags(progress_after, ("action:recover_medallion",))
        object_after = replace(
            object_after,
            o2_medallion=replace(
                object_after.o2_medallion,
                status="recovered",
                location="player_inventory",
            ),
        )
        applied_actions = ("action:recover_medallion",)

    applied_outcome_flags = () if quiet else ("outcome:public_escalation",)
    outcome_after = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress_after,
        object_state=object_after,
        npc_states=npc_states,
        elapsed_seconds=elapsed_seconds,
        extra_action_flags=extra_action_flags,
        relationship_flags=relationship_flags,
        outcome_flags=tuple(sorted(set(_sorted_unique(outcome_flags)).union(applied_outcome_flags))),
    )

    status: CaseCompletionStatus = "completed" if outcome_after.recovery_success.satisfied else "blocked"
    code = "recovery_success_completed" if status == "completed" else "recovery_completion_requirements_unmet"

    return CaseCompletionAttemptResult(
        path="recovery",
        status=status,
        code=code,
        accused_id=None,
        missing_scene_ids=(),
        trust_threshold=trust_threshold,
        trust_value=trust_value,
        missing_fact_ids=(),
        missing_item_ids=(),
        missing_action_flags=(),
        applied_action_flags=applied_actions,
        applied_outcome_flags=applied_outcome_flags,
        progress_before=progress,
        progress_after=progress_after,
        object_state_before=object_state,
        object_state_after=object_after,
        outcome_before=outcome_before,
        outcome_after=outcome_after,
    )


def attempt_accusation_completion(
    *,
    case_state: CaseState,
    progress: InvestigationProgressState,
    object_state: MbamObjectStateBundle | None,
    dialogue_runtime_state: DialogueSceneRuntimeState | None,
    npc_states: Mapping[FixedCastId, NPCState] | None,
    elapsed_seconds: float,
    accused_id: str,
    extra_action_flags: Iterable[str] = (),
    relationship_flags: Iterable[str] = (),
    outcome_flags: Iterable[str] = (),
    public: bool = False,
) -> CaseCompletionAttemptResult:
    outcome_before = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        elapsed_seconds=elapsed_seconds,
        extra_action_flags=extra_action_flags,
        relationship_flags=relationship_flags,
        outcome_flags=outcome_flags,
    )

    if not _is_valid_culprit_id(accused_id):
        return CaseCompletionAttemptResult(
            path="accusation",
            status="invalid",
            code="invalid_accused_id",
            accused_id=None,
            missing_scene_ids=(),
            trust_threshold=None,
            trust_value=None,
            missing_fact_ids=(),
            missing_item_ids=(),
            missing_action_flags=(),
            applied_action_flags=(),
            applied_outcome_flags=(),
            progress_before=progress,
            progress_after=progress,
            object_state_before=object_state,
            object_state_after=object_state,
            outcome_before=outcome_before,
            outcome_after=outcome_before,
        )

    accused = cast(CulpritId, accused_id)

    missing_scene_ids, trust_threshold, trust_value = _scene_prereq_for_confrontation(
        case_state,
        dialogue_runtime_state,
        npc_states,
    )
    if missing_scene_ids:
        return CaseCompletionAttemptResult(
            path="accusation",
            status="blocked",
            code="scene_or_trust_prerequisite_missing",
            accused_id=accused,
            missing_scene_ids=missing_scene_ids,
            trust_threshold=trust_threshold,
            trust_value=trust_value,
            missing_fact_ids=(),
            missing_item_ids=(),
            missing_action_flags=(),
            applied_action_flags=(),
            applied_outcome_flags=(),
            progress_before=progress,
            progress_after=progress,
            object_state_before=object_state,
            object_state_after=object_state,
            outcome_before=outcome_before,
            outcome_after=outcome_before,
        )

    known_facts = set(progress.known_fact_ids)
    known_items = set(progress.discovered_evidence_ids).union(progress.collected_evidence_ids)
    known_actions = set(progress.satisfied_action_flags).union(_sorted_unique(extra_action_flags))

    if accused == case_state.roles_assignment.culprit:
        ignore = tuple(action for action in case_state.resolution_rules.accusation_success.required_actions if action.startswith("action:accuse_"))
        missing_facts, missing_items, missing_actions = _missing_requirement_parts(
            case_state.resolution_rules.accusation_success,
            known_facts=known_facts,
            known_items=known_items,
            known_actions=known_actions,
            ignore_actions=ignore,
        )
        if missing_facts or missing_items or missing_actions:
            return CaseCompletionAttemptResult(
                path="accusation",
                status="blocked",
                code="accusation_prerequisites_missing",
                accused_id=accused,
                missing_scene_ids=(),
                trust_threshold=trust_threshold,
                trust_value=trust_value,
                missing_fact_ids=missing_facts,
                missing_item_ids=missing_items,
                missing_action_flags=missing_actions,
                applied_action_flags=(),
                applied_outcome_flags=(),
                progress_before=progress,
                progress_after=progress,
                object_state_before=object_state,
                object_state_after=object_state,
                outcome_before=outcome_before,
                outcome_after=outcome_before,
            )

        applied_actions = (f"action:accuse_{accused}",)
        progress_after = _with_added_action_flags(progress, applied_actions)
        applied_outcome_flags = () if not public else ("outcome:public_escalation",)
        outcome_after = evaluate_mbam_case_outcome(
            case_state=case_state,
            progress=progress_after,
            object_state=object_state,
            npc_states=npc_states,
            elapsed_seconds=elapsed_seconds,
            extra_action_flags=extra_action_flags,
            relationship_flags=relationship_flags,
            outcome_flags=tuple(sorted(set(_sorted_unique(outcome_flags)).union(applied_outcome_flags))),
        )
        status: CaseCompletionStatus = "completed" if outcome_after.accusation_success.satisfied else "blocked"
        code = "accusation_success_completed" if status == "completed" else "accusation_completion_requirements_unmet"

        return CaseCompletionAttemptResult(
            path="accusation",
            status=status,
            code=code,
            accused_id=accused,
            missing_scene_ids=(),
            trust_threshold=trust_threshold,
            trust_value=trust_value,
            missing_fact_ids=(),
            missing_item_ids=(),
            missing_action_flags=(),
            applied_action_flags=applied_actions,
            applied_outcome_flags=applied_outcome_flags,
            progress_before=progress,
            progress_after=progress_after,
            object_state_before=object_state,
            object_state_after=object_state,
            outcome_before=outcome_before,
            outcome_after=outcome_after,
        )

    # Wrong accusation path: deterministic soft-fail branch.
    applied_actions = ("action:wrong_accusation",)
    progress_after = _with_added_action_flags(progress, applied_actions)
    applied_outcome_flags = () if not public else ("outcome:public_escalation",)
    outcome_after = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress_after,
        object_state=object_state,
        npc_states=npc_states,
        elapsed_seconds=elapsed_seconds,
        extra_action_flags=extra_action_flags,
        relationship_flags=relationship_flags,
        outcome_flags=tuple(sorted(set(_sorted_unique(outcome_flags)).union(applied_outcome_flags))),
    )

    status = "completed" if outcome_after.soft_fail.triggered else "blocked"
    code = "wrong_accusation_soft_fail" if status == "completed" else "wrong_accusation_unresolved"
    return CaseCompletionAttemptResult(
        path="accusation",
        status=status,
        code=code,
        accused_id=accused,
        missing_scene_ids=(),
        trust_threshold=trust_threshold,
        trust_value=trust_value,
        missing_fact_ids=(),
        missing_item_ids=(),
        missing_action_flags=(),
        applied_action_flags=applied_actions,
        applied_outcome_flags=applied_outcome_flags,
        progress_before=progress,
        progress_after=progress_after,
        object_state_before=object_state,
        object_state_after=object_state,
        outcome_before=outcome_before,
        outcome_after=outcome_after,
    )


def _continuity_flags_from_outcome_flags(flags: Iterable[str]) -> tuple[str, ...]:
    out: set[str] = set()
    flag_set = set(_sorted_unique(flags))
    out.update(flag for flag in flag_set if flag.startswith("continuity:"))
    if "item_leaves_building" in flag_set or "outcome:item_left_building" in flag_set:
        out.add("continuity:item_left_building")
    if "relationship_penalty_future_case" in flag_set:
        out.add("continuity:relationship_penalty")
    if "outcome:best_outcome_awarded" in flag_set:
        out.add("continuity:mbam_best_outcome")
    if "outcome:soft_fail_latched" in flag_set:
        out.add("continuity:mbam_soft_fail")
    return tuple(sorted(out))


def apply_outcome_branch_transitions(
    *,
    case_state: CaseState,
    progress: InvestigationProgressState,
    object_state: MbamObjectStateBundle | None,
    npc_states: Mapping[FixedCastId, NPCState] | None,
    elapsed_seconds: float,
    extra_action_flags: Iterable[str] = (),
    relationship_flags: Iterable[str] = (),
    outcome_flags: Iterable[str] = (),
) -> OutcomeBranchTransitionResult:
    """Apply deterministic soft-fail / best-outcome branch transitions.

    This pass latches MBAM-specific branch flags so recap/replay flows can use a
    stable explicit result state rather than inferring branch outcomes from UI.
    """
    flags_before = _sorted_unique(outcome_flags)
    flag_set = set(flags_before)
    progress_after = progress
    object_after = object_state

    outcome_before = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress,
        object_state=object_state,
        npc_states=npc_states,
        elapsed_seconds=elapsed_seconds,
        extra_action_flags=extra_action_flags,
        relationship_flags=relationship_flags,
        outcome_flags=flags_before,
    )

    soft_fail_applied = False
    if outcome_before.soft_fail.triggered:
        prior_count = len(flag_set)
        flag_set.add("outcome:soft_fail_latched")
        for outcome_flag in outcome_before.soft_fail.outcome_flags:
            flag_set.add(outcome_flag)
        if "item_leaves_building" in outcome_before.soft_fail.outcome_flags:
            flag_set.add("outcome:item_left_building")
            if object_after is not None and object_after.o2_medallion.status != "recovered":
                object_after = replace(
                    object_after,
                    o2_medallion=replace(
                        object_after.o2_medallion,
                        status="missing",
                        location="unknown",
                    ),
                )
        soft_fail_applied = len(flag_set) > prior_count

    interim_flags = tuple(sorted(flag_set))
    outcome_interim = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress_after,
        object_state=object_after,
        npc_states=npc_states,
        elapsed_seconds=elapsed_seconds,
        extra_action_flags=extra_action_flags,
        relationship_flags=relationship_flags,
        outcome_flags=interim_flags,
    )

    best_outcome_applied = False
    if outcome_interim.best_outcome.satisfied:
        prior_count = len(flag_set)
        flag_set.add("outcome:best_outcome_awarded")
        if outcome_interim.quiet_recovery:
            flag_set.add("continuity:quiet_recovery")
        if not outcome_interim.public_escalation:
            flag_set.add("continuity:no_public_escalation")
        if {"rel_elodie_positive", "rel_marc_positive"}.issubset(set(outcome_interim.relationship_flags)):
            flag_set.add("continuity:strong_key_trust")
        best_outcome_applied = len(flag_set) > prior_count

    final_flags = tuple(sorted(flag_set))
    outcome_after = evaluate_mbam_case_outcome(
        case_state=case_state,
        progress=progress_after,
        object_state=object_after,
        npc_states=npc_states,
        elapsed_seconds=elapsed_seconds,
        extra_action_flags=extra_action_flags,
        relationship_flags=relationship_flags,
        outcome_flags=final_flags,
    )
    continuity_flags = _continuity_flags_from_outcome_flags(final_flags)
    applied = tuple(sorted(set(final_flags).difference(flags_before)))

    return OutcomeBranchTransitionResult(
        progress_before=progress,
        progress_after=progress_after,
        object_state_before=object_state,
        object_state_after=object_after,
        outcome_flags_before=flags_before,
        outcome_flags_after=final_flags,
        continuity_flags=continuity_flags,
        applied_outcome_flags=applied,
        soft_fail_applied=soft_fail_applied,
        best_outcome_applied=best_outcome_applied,
        outcome_before=outcome_before,
        outcome_after=outcome_after,
    )


__all__ = [
    "CaseCompletionPath",
    "CaseCompletionStatus",
    "CaseCompletionAttemptResult",
    "OutcomeBranchTransitionResult",
    "attempt_recovery_completion",
    "attempt_accusation_completion",
    "apply_outcome_branch_transitions",
]
