from __future__ import annotations

"""Deterministic MBAM outcome evaluator (Phase 7A).

This module evaluates MBAM case outcomes from canonical CaseState rules and
runtime progression surfaces. It is MBAM-specific and intentionally explicit.
"""

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import is_dataclass
import re
from typing import Any, Iterable, Literal, Mapping

from .cast_registry import FixedCastId
from .dialogue_domain import DialogueTurnRequest
from .dialogue_runtime import DialogueSceneTurnExecutionResult, DialogueTurnLogEntry
from .investigation_progress import InvestigationProgressState
from .models import BestOutcomeRule, CaseState, ResolutionRequirement, SoftFailRule
from .npc_state import NPCState
from .object_state import MbamObjectStateBundle


OutcomePrimary = Literal[
    "in_progress",
    "recovery_success",
    "accusation_success",
    "soft_fail",
    "best_outcome",
]

_CLOCK_POST_WITHOUT_RECOVERY_RE = re.compile(r"^clock:post_T_PLUS_(\d+)_without_recovery$")


def _sorted_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({v for v in values if isinstance(v, str) and v}))


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return value


def _visible_continuity_flags(debug_outcome_flags: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(flag for flag in debug_outcome_flags if flag.startswith("continuity:")))


def _person_slot_value(request: DialogueTurnRequest) -> str | None:
    for slot in request.provided_slots:
        if slot.slot_name == "person":
            return slot.value
    return None


def _normalize_accused_person(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    lowered = raw_value.strip().lower()
    if not lowered:
        return None
    if "samira" in lowered:
        return "samira"
    if "laurent" in lowered:
        return "laurent"
    outsider_tokens = (
        "outsider",
        "inconnu",
        "inconnue",
        "exterieur",
        "extérieur",
        "etranger",
        "étranger",
    )
    if any(token in lowered for token in outsider_tokens):
        return "outsider"
    return None


def _is_polite_gate_request(request: DialogueTurnRequest) -> bool:
    text = (request.utterance_text or "").strip().lower()
    if text.startswith("register:wrong"):
        return False
    if text.startswith("tone:aggressive"):
        return False
    return True


def action_flags_from_dialogue_turn(
    case_state: CaseState,
    request: DialogueTurnRequest,
    result: DialogueSceneTurnExecutionResult,
    *,
    prior_summary_pass_count: int = 0,
) -> tuple[str, ...]:
    """Derive deterministic outcome-relevant action flags from one dialogue turn."""
    flags: set[str] = set()
    if result.turn_result.status != "accepted":
        return ()

    if request.intent_id in {"request_access", "request_permission"} and _is_polite_gate_request(request):
        flags.add("action:polite_gate_usage")

    if request.intent_id == "challenge_contradiction":
        if {"N3", "N4"}.issubset(set(request.presented_fact_ids)):
            flags.add("action:state_contradiction_N3_N4")

    if request.intent_id == "summarize_understanding":
        summary_passed = False
        if result.summary_check is not None:
            summary_passed = result.summary_check.code == "summary_passed"
        elif result.turn_result.summary_check_passed is not None:
            summary_passed = bool(result.turn_result.summary_check_passed)
        if summary_passed and int(prior_summary_pass_count) + 1 >= 2:
            flags.add("action:french_summary_x2")

    if request.intent_id == "accuse":
        accused = _normalize_accused_person(_person_slot_value(request))
        if accused is None:
            flags.add("action:wrong_accusation")
        elif accused == case_state.roles_assignment.culprit:
            flags.add(f"action:accuse_{accused}")
        else:
            flags.add("action:wrong_accusation")

    return tuple(sorted(flags))


def _evaluate_requirement(
    requirement: ResolutionRequirement,
    *,
    known_fact_ids: set[str],
    known_item_ids: set[str],
    action_flags: set[str],
) -> "RequirementEvaluation":
    missing_facts = tuple(sorted(fact_id for fact_id in requirement.required_fact_ids if fact_id not in known_fact_ids))
    missing_items = tuple(sorted(item_id for item_id in requirement.required_items if item_id not in known_item_ids))
    missing_actions = tuple(sorted(action for action in requirement.required_actions if action not in action_flags))
    return RequirementEvaluation(
        satisfied=not (missing_facts or missing_items or missing_actions),
        required_fact_ids=requirement.required_fact_ids,
        required_item_ids=requirement.required_items,
        required_action_flags=requirement.required_actions,
        missing_fact_ids=missing_facts,
        missing_item_ids=missing_items,
        missing_action_flags=missing_actions,
    )


def _evaluate_best_outcome(
    rule: BestOutcomeRule,
    *,
    known_fact_ids: set[str],
    known_item_ids: set[str],
    action_flags: set[str],
    relationship_flags: set[str],
    quiet_recovery: bool,
    public_escalation: bool,
) -> "BestOutcomeEvaluation":
    base = _evaluate_requirement(
        ResolutionRequirement(
            required_fact_ids=rule.required_fact_ids,
            required_items=rule.required_items,
            required_actions=rule.required_actions,
        ),
        known_fact_ids=known_fact_ids,
        known_item_ids=known_item_ids,
        action_flags=action_flags,
    )
    missing_relationships = tuple(
        sorted(flag for flag in rule.required_relationship_flags if flag not in relationship_flags)
    )
    satisfied = base.satisfied and not missing_relationships and quiet_recovery and not public_escalation
    return BestOutcomeEvaluation(
        satisfied=satisfied,
        required_fact_ids=base.required_fact_ids,
        required_item_ids=base.required_item_ids,
        required_action_flags=base.required_action_flags,
        missing_fact_ids=base.missing_fact_ids,
        missing_item_ids=base.missing_item_ids,
        missing_action_flags=base.missing_action_flags,
        required_relationship_flags=rule.required_relationship_flags,
        missing_relationship_flags=missing_relationships,
        quiet_recovery_required=True,
        quiet_recovery_satisfied=quiet_recovery,
        public_escalation=public_escalation,
    )


def _soft_fail_condition_satisfied(
    condition: str,
    *,
    action_flags: set[str],
    outcome_flags: set[str],
    elapsed_seconds: float,
    medallion_recovered: bool,
) -> bool:
    if condition.startswith("action:"):
        return condition in action_flags
    match = _CLOCK_POST_WITHOUT_RECOVERY_RE.match(condition)
    if match is not None:
        threshold_minutes = int(match.group(1))
        return float(elapsed_seconds) >= float(threshold_minutes * 60) and not medallion_recovered
    if condition.startswith("flag:"):
        return condition in outcome_flags
    return condition in outcome_flags


def _evaluate_soft_fail(
    rule: SoftFailRule,
    *,
    action_flags: set[str],
    outcome_flags: set[str],
    elapsed_seconds: float,
    medallion_recovered: bool,
) -> "SoftFailEvaluation":
    matched = tuple(
        sorted(
            condition
            for condition in rule.trigger_conditions
            if _soft_fail_condition_satisfied(
                condition,
                action_flags=action_flags,
                outcome_flags=outcome_flags,
                elapsed_seconds=elapsed_seconds,
                medallion_recovered=medallion_recovered,
            )
        )
    )
    missing = tuple(sorted(condition for condition in rule.trigger_conditions if condition not in set(matched)))
    return SoftFailEvaluation(
        triggered=bool(matched),
        trigger_conditions=rule.trigger_conditions,
        matched_trigger_conditions=matched,
        missing_trigger_conditions=missing,
        outcome_flags=rule.outcome_flags if matched else (),
    )


def _derive_relationship_flags(npc_states: Mapping[FixedCastId, NPCState]) -> tuple[str, ...]:
    flags: set[str] = set()
    elodie = npc_states.get("elodie")
    marc = npc_states.get("marc")
    # Conservative baseline until richer relationship tracking exists.
    if elodie is not None and elodie.trust >= 0.0 and elodie.stress <= 0.8:
        flags.add("rel_elodie_positive")
    if marc is not None and marc.trust >= 0.0 and marc.stress <= 0.8:
        flags.add("rel_marc_positive")
    return tuple(sorted(flags))


@dataclass(frozen=True)
class RequirementEvaluation:
    satisfied: bool
    required_fact_ids: tuple[str, ...]
    required_item_ids: tuple[str, ...]
    required_action_flags: tuple[str, ...]
    missing_fact_ids: tuple[str, ...]
    missing_item_ids: tuple[str, ...]
    missing_action_flags: tuple[str, ...]


@dataclass(frozen=True)
class SoftFailEvaluation:
    triggered: bool
    trigger_conditions: tuple[str, ...]
    matched_trigger_conditions: tuple[str, ...]
    missing_trigger_conditions: tuple[str, ...]
    outcome_flags: tuple[str, ...]


@dataclass(frozen=True)
class BestOutcomeEvaluation(RequirementEvaluation):
    required_relationship_flags: tuple[str, ...]
    missing_relationship_flags: tuple[str, ...]
    quiet_recovery_required: bool
    quiet_recovery_satisfied: bool
    public_escalation: bool


@dataclass(frozen=True)
class MbamOutcomeEvaluationResult:
    case_id: str
    seed: str
    elapsed_seconds: float
    primary_outcome: OutcomePrimary
    terminal: bool
    recovery_success: RequirementEvaluation
    accusation_success: RequirementEvaluation
    soft_fail: SoftFailEvaluation
    best_outcome: BestOutcomeEvaluation
    contradiction_required_for_accusation: bool
    contradiction_requirement_satisfied: bool
    quiet_recovery: bool
    public_escalation: bool
    medallion_status: str | None
    known_fact_ids: tuple[str, ...]
    known_item_ids: tuple[str, ...]
    action_flags: tuple[str, ...]
    relationship_flags: tuple[str, ...]
    debug_outcome_flags: tuple[str, ...]


def evaluate_mbam_case_outcome(
    *,
    case_state: CaseState,
    progress: InvestigationProgressState,
    object_state: MbamObjectStateBundle | None = None,
    npc_states: Mapping[FixedCastId, NPCState] | None = None,
    dialogue_turn_log: tuple[DialogueTurnLogEntry, ...] = (),
    elapsed_seconds: float = 0.0,
    extra_action_flags: Iterable[str] = (),
    relationship_flags: Iterable[str] = (),
    outcome_flags: Iterable[str] = (),
) -> MbamOutcomeEvaluationResult:
    """Evaluate deterministic MBAM outcomes from canonical case rules + runtime state."""
    known_fact_ids = set(progress.known_fact_ids)
    known_item_ids = set(progress.discovered_evidence_ids).union(progress.collected_evidence_ids)
    action_flags = set(progress.satisfied_action_flags).union(extra_action_flags)
    derived_relationship_flags = set(relationship_flags)
    if npc_states is not None:
        derived_relationship_flags.update(_derive_relationship_flags(npc_states))
    debug_outcome_flags = set(_sorted_unique(outcome_flags))

    summary_pass_count = sum(1 for row in dialogue_turn_log if row.summary_check_code == "summary_passed")
    if summary_pass_count >= 2:
        action_flags.add("action:french_summary_x2")

    medallion_status: str | None = None
    medallion_recovered = False
    if object_state is not None:
        medallion_status = object_state.o2_medallion.status
        medallion_recovered = medallion_status == "recovered"
        if medallion_recovered:
            action_flags.add("action:recover_medallion")

    public_escalation = (
        "outcome:public_escalation" in debug_outcome_flags
        or "action:public_accusation" in action_flags
        or "action:wrong_accusation" in action_flags
    )
    quiet_recovery = medallion_recovered and not public_escalation

    recovery_eval = _evaluate_requirement(
        case_state.resolution_rules.recovery_success,
        known_fact_ids=known_fact_ids,
        known_item_ids=known_item_ids,
        action_flags=action_flags,
    )
    accusation_eval = _evaluate_requirement(
        case_state.resolution_rules.accusation_success,
        known_fact_ids=known_fact_ids,
        known_item_ids=known_item_ids,
        action_flags=action_flags,
    )
    soft_fail_eval = _evaluate_soft_fail(
        case_state.resolution_rules.soft_fail,
        action_flags=action_flags,
        outcome_flags=debug_outcome_flags,
        elapsed_seconds=elapsed_seconds,
        medallion_recovered=medallion_recovered,
    )
    if soft_fail_eval.triggered:
        debug_outcome_flags.update(soft_fail_eval.outcome_flags)

    best_eval = _evaluate_best_outcome(
        case_state.resolution_rules.best_outcome,
        known_fact_ids=known_fact_ids,
        known_item_ids=known_item_ids,
        action_flags=action_flags,
        relationship_flags=derived_relationship_flags,
        quiet_recovery=quiet_recovery,
        public_escalation=public_escalation,
    )

    required_contradiction_actions = tuple(
        action
        for action in case_state.resolution_rules.accusation_success.required_actions
        if action.startswith("action:state_contradiction_")
    )
    contradiction_required = bool(required_contradiction_actions)
    contradiction_satisfied = all(action in action_flags for action in required_contradiction_actions)

    if best_eval.satisfied:
        primary: OutcomePrimary = "best_outcome"
    elif soft_fail_eval.triggered:
        primary = "soft_fail"
    elif recovery_eval.satisfied:
        primary = "recovery_success"
    elif accusation_eval.satisfied:
        primary = "accusation_success"
    else:
        primary = "in_progress"

    return MbamOutcomeEvaluationResult(
        case_id=case_state.case_id,
        seed=case_state.seed,
        elapsed_seconds=float(elapsed_seconds),
        primary_outcome=primary,
        terminal=primary != "in_progress",
        recovery_success=recovery_eval,
        accusation_success=accusation_eval,
        soft_fail=soft_fail_eval,
        best_outcome=best_eval,
        contradiction_required_for_accusation=contradiction_required,
        contradiction_requirement_satisfied=contradiction_satisfied,
        quiet_recovery=quiet_recovery,
        public_escalation=public_escalation,
        medallion_status=medallion_status,
        known_fact_ids=tuple(sorted(known_fact_ids)),
        known_item_ids=tuple(sorted(known_item_ids)),
        action_flags=tuple(sorted(action_flags)),
        relationship_flags=tuple(sorted(derived_relationship_flags)),
        debug_outcome_flags=tuple(sorted(debug_outcome_flags)),
    )


def build_visible_outcome_projection(
    evaluation: MbamOutcomeEvaluationResult,
    *,
    truth_epoch: int = 1,
) -> dict[str, Any]:
    epoch = int(truth_epoch)
    if epoch <= 0:
        raise ValueError("truth_epoch must be >= 1")
    return {
        "truth_epoch": epoch,
        "primary_outcome": evaluation.primary_outcome,
        "terminal": evaluation.terminal,
        "recovery_success": evaluation.recovery_success.satisfied,
        "accusation_success": evaluation.accusation_success.satisfied,
        "soft_fail": evaluation.soft_fail.triggered,
        "best_outcome": evaluation.best_outcome.satisfied,
        "contradiction_required_for_accusation": evaluation.contradiction_required_for_accusation,
        "contradiction_requirement_satisfied": evaluation.contradiction_requirement_satisfied,
        "quiet_recovery": evaluation.quiet_recovery,
        "public_escalation": evaluation.public_escalation,
        "soft_fail_latched": "outcome:soft_fail_latched" in set(evaluation.debug_outcome_flags),
        "best_outcome_awarded": "outcome:best_outcome_awarded" in set(evaluation.debug_outcome_flags),
        "soft_fail_reasons": list(evaluation.soft_fail.matched_trigger_conditions),
        "continuity_flags": list(_visible_continuity_flags(evaluation.debug_outcome_flags)),
    }


def build_debug_outcome_projection(
    evaluation: MbamOutcomeEvaluationResult,
    *,
    truth_epoch: int = 1,
) -> dict[str, Any]:
    epoch = int(truth_epoch)
    if epoch <= 0:
        raise ValueError("truth_epoch must be >= 1")
    return {
        "debug_scope": "outcome_state_private",
        "case_id": evaluation.case_id,
        "seed": evaluation.seed,
        "truth_epoch": epoch,
        "evaluation": _to_jsonable(evaluation),
    }


__all__ = [
    "OutcomePrimary",
    "RequirementEvaluation",
    "SoftFailEvaluation",
    "BestOutcomeEvaluation",
    "MbamOutcomeEvaluationResult",
    "action_flags_from_dialogue_turn",
    "evaluate_mbam_case_outcome",
    "build_visible_outcome_projection",
    "build_debug_outcome_projection",
]
