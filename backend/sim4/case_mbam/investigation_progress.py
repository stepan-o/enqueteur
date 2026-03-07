from __future__ import annotations

"""MBAM evidence + fact + contradiction progression substrate (Phase 3D)."""

from dataclasses import dataclass
from typing import Iterable, Literal

from .investigation_execution import InvestigationExecutionResult
from .models import CaseState


ContradictionExecStatus = Literal["success", "blocked", "invalid"]


def _sorted_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({v for v in values if isinstance(v, str) and v}))


@dataclass(frozen=True)
class InvestigationProgressState:
    discovered_evidence_ids: tuple[str, ...] = ()
    collected_evidence_ids: tuple[str, ...] = ()
    observed_clue_ids: tuple[str, ...] = ()
    known_fact_ids: tuple[str, ...] = ()
    unlockable_contradiction_edge_ids: tuple[str, ...] = ()
    known_contradiction_edge_ids: tuple[str, ...] = ()
    consumed_action_keys: tuple[str, ...] = ()
    satisfied_action_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "discovered_evidence_ids", _sorted_unique(self.discovered_evidence_ids))
        object.__setattr__(self, "collected_evidence_ids", _sorted_unique(self.collected_evidence_ids))
        object.__setattr__(self, "observed_clue_ids", _sorted_unique(self.observed_clue_ids))
        object.__setattr__(self, "known_fact_ids", _sorted_unique(self.known_fact_ids))
        object.__setattr__(
            self,
            "unlockable_contradiction_edge_ids",
            _sorted_unique(self.unlockable_contradiction_edge_ids),
        )
        object.__setattr__(self, "known_contradiction_edge_ids", _sorted_unique(self.known_contradiction_edge_ids))
        object.__setattr__(self, "consumed_action_keys", _sorted_unique(self.consumed_action_keys))
        object.__setattr__(self, "satisfied_action_flags", _sorted_unique(self.satisfied_action_flags))


@dataclass(frozen=True)
class InvestigationProgressUpdate:
    progress_before: InvestigationProgressState
    progress_after: InvestigationProgressState
    newly_discovered_evidence_ids: tuple[str, ...]
    newly_collected_evidence_ids: tuple[str, ...]
    newly_observed_clue_ids: tuple[str, ...]
    newly_known_fact_ids: tuple[str, ...]
    newly_unlockable_contradiction_edge_ids: tuple[str, ...]
    newly_known_contradiction_edge_ids: tuple[str, ...]
    contradiction_required_for_accusation: bool
    contradiction_requirement_satisfied: bool


@dataclass(frozen=True)
class ContradictionExecutionResult:
    status: ContradictionExecStatus
    code: str
    edge_id: str
    required_fact_ids: tuple[str, ...]
    missing_fact_ids: tuple[str, ...]
    action_flag: str | None
    progress_before: InvestigationProgressState
    progress_after: InvestigationProgressState


_EVIDENCE_TO_FACTS: dict[str, tuple[str, ...]] = {
    "E1_TORN_NOTE": ("N6",),
    "E2_CAFE_RECEIPT": ("N4",),
    "E3_METHOD_TRACE": ("N7",),
}


def build_initial_investigation_progress(case_state: CaseState) -> InvestigationProgressState:
    """Build deterministic starting progress from visible CaseState slice."""
    known_facts = tuple(case_state.visible_case_slice.starting_known_fact_ids)
    unlockable = _compute_unlockable_contradictions(case_state, known_facts)
    return InvestigationProgressState(
        discovered_evidence_ids=(),
        collected_evidence_ids=(),
        observed_clue_ids=(),
        known_fact_ids=known_facts,
        unlockable_contradiction_edge_ids=unlockable,
        known_contradiction_edge_ids=(),
        consumed_action_keys=(),
        satisfied_action_flags=(),
    )


def _legal_fact_ids(case_state: CaseState, fact_ids: Iterable[str]) -> tuple[str, ...]:
    nodes = {n.fact_id: n for n in case_state.truth_graph.nodes}
    legal: list[str] = []
    for fact_id in fact_ids:
        node = nodes.get(fact_id)
        if node is None:
            continue
        if node.visibility == "hidden":
            continue
        legal.append(fact_id)
    return _sorted_unique(legal)


def _compute_unlockable_contradictions(case_state: CaseState, known_fact_ids: Iterable[str]) -> tuple[str, ...]:
    known = set(known_fact_ids)
    unlockable: list[str] = []
    for edge in case_state.truth_graph.edges:
        if edge.relation != "contradicts":
            continue
        if edge.from_fact_id in known and edge.to_fact_id in known:
            unlockable.append(edge.edge_id)
    return _sorted_unique(unlockable)


def _evidence_auto_collect_policy(
    *,
    object_id: str,
    affordance_id: str,
    evidence_id: str,
) -> bool:
    if evidence_id == "E3_METHOD_TRACE":
        return False
    if object_id == "O4_BENCH" and affordance_id == "inspect":
        return True
    if object_id == "O9_RECEIPT_PRINTER" and affordance_id == "ask_for_receipt":
        return True
    return False


def _contradiction_action_flag(case_state: CaseState, edge_id: str) -> str:
    edge = next((e for e in case_state.truth_graph.edges if e.edge_id == edge_id), None)
    if edge is None:
        return f"action:state_contradiction_edge_{edge_id}"
    if {edge.from_fact_id, edge.to_fact_id} == {"N3", "N4"}:
        return "action:state_contradiction_N3_N4"
    return f"action:state_contradiction_{edge.from_fact_id}_{edge.to_fact_id}"


def contradiction_required_for_accusation(case_state: CaseState) -> bool:
    return any(
        action.startswith("action:state_contradiction_")
        for action in case_state.resolution_rules.accusation_success.required_actions
    )


def contradiction_requirement_satisfied_for_accusation(
    case_state: CaseState,
    progress: InvestigationProgressState,
) -> bool:
    required = tuple(
        action
        for action in case_state.resolution_rules.accusation_success.required_actions
        if action.startswith("action:state_contradiction_")
    )
    if not required:
        return True
    satisfied = set(progress.satisfied_action_flags)
    return all(action in satisfied for action in required)


def apply_execution_result_to_progress(
    case_state: CaseState,
    progress: InvestigationProgressState,
    execution: InvestigationExecutionResult,
) -> InvestigationProgressUpdate:
    """Apply one affordance execution result to evidence/fact/contradiction progress."""
    discovered = set(progress.discovered_evidence_ids)
    collected = set(progress.collected_evidence_ids)
    observed = set(progress.observed_clue_ids)
    known_facts = set(progress.known_fact_ids)
    known_contradictions = set(progress.known_contradiction_edge_ids)
    consumed_action_keys = set(progress.consumed_action_keys)
    satisfied_actions = set(progress.satisfied_action_flags)

    newly_discovered: set[str] = set()
    newly_collected: set[str] = set()
    newly_observed: set[str] = set()
    newly_known_facts: set[str] = set()
    newly_unlockable_contradictions: set[str] = set()

    if execution.ack.kind in {"success", "no_op"}:
        obs_id = f"obs:{execution.command.object_id}:{execution.command.affordance_id}"
        if obs_id not in observed:
            observed.add(obs_id)
            newly_observed.add(obs_id)

    if execution.consumed_action_key is not None:
        if execution.consumed_action_key not in consumed_action_keys:
            consumed_action_keys.add(execution.consumed_action_key)

    if execution.ack.kind in {"success", "no_op"}:
        fact_candidates = _legal_fact_ids(case_state, execution.fact_unlock_candidates)
        for fact_id in fact_candidates:
            if fact_id not in known_facts:
                known_facts.add(fact_id)
                newly_known_facts.add(fact_id)

        for evidence_id in execution.revealed_evidence_ids:
            if evidence_id not in discovered:
                discovered.add(evidence_id)
                newly_discovered.add(evidence_id)
            auto_collect = _evidence_auto_collect_policy(
                object_id=execution.command.object_id,
                affordance_id=execution.command.affordance_id,
                evidence_id=evidence_id,
            )
            if auto_collect and evidence_id not in collected:
                collected.add(evidence_id)
                newly_collected.add(evidence_id)
            if not auto_collect:
                clue_id = f"clue:evidence:{evidence_id}:observed_not_collected"
                if clue_id not in observed:
                    observed.add(clue_id)
                    newly_observed.add(clue_id)

            for fact_id in _legal_fact_ids(case_state, _EVIDENCE_TO_FACTS.get(evidence_id, ())):
                if fact_id not in known_facts:
                    known_facts.add(fact_id)
                    newly_known_facts.add(fact_id)

    # recompute contradiction unlocks from canonical truth graph only.
    unlockable = set(_compute_unlockable_contradictions(case_state, known_facts))
    for edge_id in unlockable:
        if edge_id not in progress.unlockable_contradiction_edge_ids:
            newly_unlockable_contradictions.add(edge_id)
    known_contradictions.intersection_update(unlockable)

    after = InvestigationProgressState(
        discovered_evidence_ids=tuple(discovered),
        collected_evidence_ids=tuple(collected),
        observed_clue_ids=tuple(observed),
        known_fact_ids=tuple(known_facts),
        unlockable_contradiction_edge_ids=tuple(unlockable),
        known_contradiction_edge_ids=tuple(known_contradictions),
        consumed_action_keys=tuple(consumed_action_keys),
        satisfied_action_flags=tuple(satisfied_actions),
    )

    return InvestigationProgressUpdate(
        progress_before=progress,
        progress_after=after,
        newly_discovered_evidence_ids=_sorted_unique(newly_discovered),
        newly_collected_evidence_ids=_sorted_unique(newly_collected),
        newly_observed_clue_ids=_sorted_unique(newly_observed),
        newly_known_fact_ids=_sorted_unique(newly_known_facts),
        newly_unlockable_contradiction_edge_ids=_sorted_unique(newly_unlockable_contradictions),
        newly_known_contradiction_edge_ids=(),
        contradiction_required_for_accusation=contradiction_required_for_accusation(case_state),
        contradiction_requirement_satisfied=contradiction_requirement_satisfied_for_accusation(case_state, after),
    )


def execute_contradiction_edge(
    case_state: CaseState,
    progress: InvestigationProgressState,
    *,
    edge_id: str,
) -> ContradictionExecutionResult:
    """Execute contradiction acknowledgement when edge ingredients are known."""
    edge = next((e for e in case_state.truth_graph.edges if e.edge_id == edge_id), None)
    if edge is None:
        return ContradictionExecutionResult(
            status="invalid",
            code="unknown_edge_id",
            edge_id=edge_id,
            required_fact_ids=(),
            missing_fact_ids=(),
            action_flag=None,
            progress_before=progress,
            progress_after=progress,
        )
    if edge.relation != "contradicts":
        return ContradictionExecutionResult(
            status="invalid",
            code="edge_not_contradiction",
            edge_id=edge_id,
            required_fact_ids=(edge.from_fact_id, edge.to_fact_id),
            missing_fact_ids=(),
            action_flag=None,
            progress_before=progress,
            progress_after=progress,
        )

    required_fact_ids = (edge.from_fact_id, edge.to_fact_id)
    known = set(progress.known_fact_ids)
    missing = tuple(sorted(f for f in required_fact_ids if f not in known))
    if missing:
        return ContradictionExecutionResult(
            status="blocked",
            code="missing_required_facts",
            edge_id=edge_id,
            required_fact_ids=required_fact_ids,
            missing_fact_ids=missing,
            action_flag=None,
            progress_before=progress,
            progress_after=progress,
        )

    if edge_id in progress.known_contradiction_edge_ids:
        action_flag = _contradiction_action_flag(case_state, edge_id)
        return ContradictionExecutionResult(
            status="success",
            code="already_known",
            edge_id=edge_id,
            required_fact_ids=required_fact_ids,
            missing_fact_ids=(),
            action_flag=action_flag,
            progress_before=progress,
            progress_after=progress,
        )

    known_contradictions = set(progress.known_contradiction_edge_ids)
    known_contradictions.add(edge_id)
    satisfied_actions = set(progress.satisfied_action_flags)
    action_flag = _contradiction_action_flag(case_state, edge_id)
    satisfied_actions.add(action_flag)

    after = InvestigationProgressState(
        discovered_evidence_ids=progress.discovered_evidence_ids,
        collected_evidence_ids=progress.collected_evidence_ids,
        observed_clue_ids=progress.observed_clue_ids,
        known_fact_ids=progress.known_fact_ids,
        unlockable_contradiction_edge_ids=progress.unlockable_contradiction_edge_ids,
        known_contradiction_edge_ids=tuple(known_contradictions),
        consumed_action_keys=progress.consumed_action_keys,
        satisfied_action_flags=tuple(satisfied_actions),
    )
    return ContradictionExecutionResult(
        status="success",
        code="contradiction_recorded",
        edge_id=edge_id,
        required_fact_ids=required_fact_ids,
        missing_fact_ids=(),
        action_flag=action_flag,
        progress_before=progress,
        progress_after=after,
    )


__all__ = [
    "ContradictionExecStatus",
    "ContradictionExecutionResult",
    "InvestigationProgressState",
    "InvestigationProgressUpdate",
    "apply_execution_result_to_progress",
    "build_initial_investigation_progress",
    "contradiction_required_for_accusation",
    "contradiction_requirement_satisfied_for_accusation",
    "execute_contradiction_edge",
]
