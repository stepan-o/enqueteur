from __future__ import annotations

"""Deterministic MBAM scene runtime and structured dialogue turn handling (Phase 4C)."""

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
import re
from typing import Iterable, Literal, Mapping

from .dialogue_domain import (
    DialogueSceneState,
    DialogueTurnRequest,
    DialogueTurnResult,
    DialogueUnlockOutputs,
    RepairResponseMode,
)
from .investigation_progress import InvestigationProgressState
from .models import CaseState, SceneCompletionState, SceneId
from .npc_state import NPCState
from .scene_definitions import (
    MbamSceneDefinition,
    MbamSceneDefinitions,
    build_mbam_scene_definitions,
    get_mbam_scene_definition,
)


SceneRuntimeOutcome = Literal["accepted", "blocked", "repair", "rejected"]
SceneEntryStatus = Literal["entered", "blocked_gate", "invalid_scene", "invalid_npc", "invalid_scene_state"]

_SCENE_ORDER: tuple[SceneId, ...] = ("S1", "S2", "S3", "S4", "S5")
_WINDOW_RE = re.compile(r"^T\+(\d{1,2})\.\.T\+(\d{1,2})$")


def _sorted_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({v for v in values if isinstance(v, str) and v}))


@dataclass(frozen=True)
class SceneGateCheckResult:
    passed: bool
    missing_fact_ids: tuple[str, ...] = ()
    missing_item_ids: tuple[str, ...] = ()
    trust_threshold: float | None = None
    trust_value: float | None = None
    time_window: str | None = None
    elapsed_seconds: float | None = None
    failure_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "missing_fact_ids", _sorted_unique(self.missing_fact_ids))
        object.__setattr__(self, "missing_item_ids", _sorted_unique(self.missing_item_ids))
        object.__setattr__(self, "failure_reasons", _sorted_unique(self.failure_reasons))


@dataclass(frozen=True)
class DialogueExecutionContext:
    known_fact_ids: tuple[str, ...] = ()
    known_evidence_ids: tuple[str, ...] = ()
    collected_evidence_ids: tuple[str, ...] = ()
    npc_states: Mapping[str, NPCState] = field(default_factory=dict)
    elapsed_seconds: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "known_fact_ids", _sorted_unique(self.known_fact_ids))
        object.__setattr__(self, "known_evidence_ids", _sorted_unique(self.known_evidence_ids))
        object.__setattr__(self, "collected_evidence_ids", _sorted_unique(self.collected_evidence_ids))
        object.__setattr__(self, "elapsed_seconds", float(self.elapsed_seconds))


@dataclass(frozen=True)
class DialogueSceneRuntimeState:
    scene_definitions: MbamSceneDefinitions
    scene_completion_states: tuple[tuple[SceneId, SceneCompletionState], ...]
    active_scene_id: SceneId | None = None
    revealed_fact_ids: tuple[str, ...] = ()
    emitted_scene_completion_flags: tuple[str, ...] = ()
    emitted_object_action_unlocks: tuple[str, ...] = ()
    surfaced_scene_ids: tuple[SceneId, ...] = ()
    turn_index: int = 0

    def __post_init__(self) -> None:
        provided_ids = tuple(scene_id for scene_id, _state in self.scene_completion_states)
        if provided_ids != _SCENE_ORDER:
            raise ValueError("scene_completion_states must cover S1..S5 in canonical order")
        object.__setattr__(self, "revealed_fact_ids", _sorted_unique(self.revealed_fact_ids))
        object.__setattr__(
            self,
            "emitted_scene_completion_flags",
            _sorted_unique(self.emitted_scene_completion_flags),
        )
        object.__setattr__(
            self,
            "emitted_object_action_unlocks",
            _sorted_unique(self.emitted_object_action_unlocks),
        )
        object.__setattr__(
            self,
            "surfaced_scene_ids",
            tuple(scene_id for scene_id in _SCENE_ORDER if scene_id in set(self.surfaced_scene_ids)),
        )
        if self.turn_index < 0:
            raise ValueError("turn_index must be >= 0")


@dataclass(frozen=True)
class DialogueSceneEnterResult:
    scene_id: SceneId
    npc_id: str
    status: SceneEntryStatus
    code: str
    gate_check: SceneGateCheckResult
    scene_state_before: DialogueSceneState
    scene_state_after: DialogueSceneState
    revealed_fact_ids: tuple[str, ...]
    runtime_before: DialogueSceneRuntimeState
    runtime_after: DialogueSceneRuntimeState


@dataclass(frozen=True)
class DialogueSceneTurnExecutionResult:
    scene_id: SceneId
    npc_id: str
    outcome: SceneRuntimeOutcome
    response_mode: Literal["accept", "block", "repair", "reject"]
    turn_result: DialogueTurnResult
    gate_check: SceneGateCheckResult
    scene_state_before: DialogueSceneState
    scene_state_after: DialogueSceneState
    runtime_before: DialogueSceneRuntimeState
    runtime_after: DialogueSceneRuntimeState


def _completion_map(state: DialogueSceneRuntimeState) -> dict[SceneId, SceneCompletionState]:
    return {scene_id: completion for scene_id, completion in state.scene_completion_states}


def _state_with_scene_state(
    definition: MbamSceneDefinition,
    completion_state: SceneCompletionState,
) -> DialogueSceneState:
    return replace(definition.scene_state, completion_state=completion_state)


def _parse_time_window_minutes(window: str) -> tuple[float, float] | None:
    match = _WINDOW_RE.match(window)
    if match is None:
        return None
    low_min = float(match.group(1))
    high_min = float(match.group(2))
    if high_min < low_min:
        return None
    return low_min, high_min


def _evaluate_scene_gate(
    definition: MbamSceneDefinition,
    *,
    context: DialogueExecutionContext,
    runtime_state: DialogueSceneRuntimeState,
) -> SceneGateCheckResult:
    gate = definition.case_gate
    known_facts = set(context.known_fact_ids).union(runtime_state.revealed_fact_ids)
    missing_facts = tuple(sorted(f for f in gate.required_fact_ids if f not in known_facts))
    known_items = set(context.collected_evidence_ids)
    missing_items = tuple(sorted(item for item in gate.required_items if item not in known_items))

    trust_value: float | None = None
    trust_threshold = gate.trust_threshold
    trust_failed = False
    npc = context.npc_states.get(definition.primary_npc_id)
    if trust_threshold is not None:
        trust_value = npc.trust if npc is not None else None
        trust_failed = trust_value is None or trust_value < trust_threshold

    time_failed = False
    if gate.time_window is not None:
        parsed = _parse_time_window_minutes(gate.time_window)
        if parsed is None:
            time_failed = True
        else:
            low_min, high_min = parsed
            elapsed_min = float(context.elapsed_seconds) / 60.0
            time_failed = not (low_min <= elapsed_min <= high_min)

    reasons: list[str] = []
    if missing_facts:
        reasons.append("missing_required_facts")
    if missing_items:
        reasons.append("missing_required_items")
    if trust_failed:
        reasons.append("trust_below_threshold")
    if time_failed:
        reasons.append("outside_time_window")

    return SceneGateCheckResult(
        passed=len(reasons) == 0,
        missing_fact_ids=missing_facts,
        missing_item_ids=missing_items,
        trust_threshold=trust_threshold,
        trust_value=trust_value,
        time_window=gate.time_window,
        elapsed_seconds=context.elapsed_seconds,
        failure_reasons=tuple(reasons),
    )


def build_dialogue_execution_context(
    progress: InvestigationProgressState,
    npc_states: Mapping[str, NPCState],
    *,
    elapsed_seconds: float,
) -> DialogueExecutionContext:
    return DialogueExecutionContext(
        known_fact_ids=progress.known_fact_ids,
        known_evidence_ids=tuple(sorted(set(progress.discovered_evidence_ids).union(progress.collected_evidence_ids))),
        collected_evidence_ids=progress.collected_evidence_ids,
        npc_states=npc_states,
        elapsed_seconds=float(elapsed_seconds),
    )


def build_initial_dialogue_scene_runtime(
    case_state: CaseState,
    *,
    context: DialogueExecutionContext | None = None,
) -> DialogueSceneRuntimeState:
    defs = build_mbam_scene_definitions(case_state)
    completion = tuple(
        (scene_id, get_mbam_scene_definition(defs, scene_id).scene_state.completion_state)
        for scene_id in _SCENE_ORDER
    )
    surfaced = tuple(
        scene_id
        for scene_id in _SCENE_ORDER
        if get_mbam_scene_definition(defs, scene_id).scene_state.completion_state in {"available", "in_progress"}
    )
    known_facts = case_state.visible_case_slice.starting_known_fact_ids
    if context is not None:
        known_facts = tuple(sorted(set(known_facts).union(context.known_fact_ids)))
    return DialogueSceneRuntimeState(
        scene_definitions=defs,
        scene_completion_states=completion,
        active_scene_id=None,
        revealed_fact_ids=known_facts,
        emitted_scene_completion_flags=(),
        emitted_object_action_unlocks=(),
        surfaced_scene_ids=surfaced,
        turn_index=0,
    )


def enter_dialogue_scene(
    case_state: CaseState,
    runtime_state: DialogueSceneRuntimeState,
    *,
    scene_id: SceneId,
    npc_id: str,
    context: DialogueExecutionContext,
) -> DialogueSceneEnterResult:
    del case_state  # scene definitions are already derived from canonical CaseState.
    completion_map = _completion_map(runtime_state)
    if scene_id not in completion_map:
        raise ValueError(f"Unknown scene id: {scene_id!r}")

    definition = get_mbam_scene_definition(runtime_state.scene_definitions, scene_id)
    before_completion = completion_map[scene_id]
    before_scene_state = _state_with_scene_state(definition, before_completion)

    if npc_id != definition.primary_npc_id:
        gate = _evaluate_scene_gate(definition, context=context, runtime_state=runtime_state)
        return DialogueSceneEnterResult(
            scene_id=scene_id,
            npc_id=npc_id,
            status="invalid_npc",
            code="scene_primary_npc_mismatch",
            gate_check=gate,
            scene_state_before=before_scene_state,
            scene_state_after=before_scene_state,
            revealed_fact_ids=(),
            runtime_before=runtime_state,
            runtime_after=runtime_state,
        )

    if before_completion in {"completed", "failed_soft"}:
        gate = _evaluate_scene_gate(definition, context=context, runtime_state=runtime_state)
        return DialogueSceneEnterResult(
            scene_id=scene_id,
            npc_id=npc_id,
            status="invalid_scene_state",
            code="scene_already_terminal",
            gate_check=gate,
            scene_state_before=before_scene_state,
            scene_state_after=before_scene_state,
            revealed_fact_ids=(),
            runtime_before=runtime_state,
            runtime_after=runtime_state,
        )

    gate_check = _evaluate_scene_gate(definition, context=context, runtime_state=runtime_state)
    if not gate_check.passed:
        return DialogueSceneEnterResult(
            scene_id=scene_id,
            npc_id=npc_id,
            status="blocked_gate",
            code=gate_check.failure_reasons[0] if gate_check.failure_reasons else "scene_gate_blocked",
            gate_check=gate_check,
            scene_state_before=before_scene_state,
            scene_state_after=before_scene_state,
            revealed_fact_ids=(),
            runtime_before=runtime_state,
            runtime_after=runtime_state,
        )

    completion_map[scene_id] = "in_progress"
    revealed = tuple(sorted(set(runtime_state.revealed_fact_ids).union(definition.scene_state.revealed_fact_ids)))
    after = DialogueSceneRuntimeState(
        scene_definitions=runtime_state.scene_definitions,
        scene_completion_states=tuple((sid, completion_map[sid]) for sid in _SCENE_ORDER),
        active_scene_id=scene_id,
        revealed_fact_ids=revealed,
        emitted_scene_completion_flags=runtime_state.emitted_scene_completion_flags,
        emitted_object_action_unlocks=runtime_state.emitted_object_action_unlocks,
        surfaced_scene_ids=tuple(sorted(set(runtime_state.surfaced_scene_ids).union({scene_id}))),
        turn_index=runtime_state.turn_index,
    )
    after_scene_state = _state_with_scene_state(definition, "in_progress")
    return DialogueSceneEnterResult(
        scene_id=scene_id,
        npc_id=npc_id,
        status="entered",
        code="scene_entered",
        gate_check=gate_check,
        scene_state_before=before_scene_state,
        scene_state_after=after_scene_state,
        revealed_fact_ids=tuple(definition.scene_state.revealed_fact_ids),
        runtime_before=runtime_state,
        runtime_after=after,
    )


def _repair_mode_for_trigger(scene_state: DialogueSceneState, trigger: str) -> RepairResponseMode:
    path = next((row for row in scene_state.repair_paths if row.trigger == trigger), None)
    if path is None:
        return "meta_hint"
    return path.response_mode


def _intent_affect(intent_id: str, status: str) -> tuple[float, float]:
    if status != "accepted":
        return 0.0, 0.0
    if intent_id == "reassure":
        return 0.04, -0.05
    if intent_id == "summarize_understanding":
        return 0.05, -0.03
    if intent_id == "present_evidence":
        return 0.03, -0.01
    if intent_id == "challenge_contradiction":
        return 0.01, 0.04
    if intent_id == "accuse":
        return -0.08, 0.10
    if intent_id in {"request_access", "request_permission"}:
        return 0.02, 0.0
    return 0.0, 0.0


def _empty_unlocks() -> DialogueUnlockOutputs:
    return DialogueUnlockOutputs()


def _outcome_from_status(status: str) -> SceneRuntimeOutcome:
    if status == "accepted":
        return "accepted"
    if status == "blocked_gate":
        return "blocked"
    if status == "repair":
        return "repair"
    return "rejected"


def _response_mode_from_outcome(outcome: SceneRuntimeOutcome) -> Literal["accept", "block", "repair", "reject"]:
    if outcome == "accepted":
        return "accept"
    if outcome == "blocked":
        return "block"
    if outcome == "repair":
        return "repair"
    return "reject"


def _known_fact_pool(
    runtime_state: DialogueSceneRuntimeState,
    context: DialogueExecutionContext,
) -> set[str]:
    return set(runtime_state.revealed_fact_ids).union(context.known_fact_ids)


def execute_dialogue_turn(
    case_state: CaseState,
    runtime_state: DialogueSceneRuntimeState,
    request: DialogueTurnRequest,
    *,
    context: DialogueExecutionContext,
) -> DialogueSceneTurnExecutionResult:
    # Ensure scene is entered and in-progress.
    enter_result = enter_dialogue_scene(
        case_state,
        runtime_state,
        scene_id=request.scene_id,
        npc_id=request.npc_id,
        context=context,
    )
    working_state = enter_result.runtime_after
    definition = get_mbam_scene_definition(working_state.scene_definitions, request.scene_id)
    completion_map = _completion_map(working_state)
    current_completion = completion_map[request.scene_id]
    scene_before = _state_with_scene_state(definition, current_completion)

    if enter_result.status != "entered" and current_completion != "in_progress":
        status = "blocked_gate" if enter_result.status == "blocked_gate" else "invalid_scene_state"
        code = enter_result.code
        turn = DialogueTurnResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            intent_id=request.intent_id,
            status=status,
            code=code,
            revealed_fact_ids=(),
            trust_delta=0.0,
            stress_delta=0.0,
            missing_required_slots=(),
            repair_response_mode=None,
            summary_check_passed=None,
            unlock_outputs=_empty_unlocks(),
        )
        scene_after = _state_with_scene_state(definition, completion_map[request.scene_id])
        outcome = _outcome_from_status(turn.status)
        return DialogueSceneTurnExecutionResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            outcome=outcome,
            response_mode=_response_mode_from_outcome(outcome),
            turn_result=turn,
            gate_check=enter_result.gate_check,
            scene_state_before=scene_before,
            scene_state_after=scene_after,
            runtime_before=runtime_state,
            runtime_after=working_state,
        )

    gate_check = _evaluate_scene_gate(definition, context=context, runtime_state=working_state)
    if not gate_check.passed:
        turn = DialogueTurnResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            intent_id=request.intent_id,
            status="blocked_gate",
            code=gate_check.failure_reasons[0] if gate_check.failure_reasons else "scene_gate_blocked",
            revealed_fact_ids=(),
            trust_delta=0.0,
            stress_delta=0.0,
            missing_required_slots=(),
            repair_response_mode=None,
            summary_check_passed=None,
            unlock_outputs=_empty_unlocks(),
        )
        scene_after = _state_with_scene_state(definition, completion_map[request.scene_id])
        outcome = _outcome_from_status(turn.status)
        return DialogueSceneTurnExecutionResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            outcome=outcome,
            response_mode=_response_mode_from_outcome(outcome),
            turn_result=turn,
            gate_check=gate_check,
            scene_state_before=scene_before,
            scene_state_after=scene_after,
            runtime_before=runtime_state,
            runtime_after=working_state,
        )

    scene_state = definition.scene_state
    if request.intent_id not in scene_state.allowed_intents:
        turn = DialogueTurnResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            intent_id=request.intent_id,
            status="invalid_intent",
            code="intent_not_allowed_for_scene",
            unlock_outputs=_empty_unlocks(),
        )
        scene_after = _state_with_scene_state(definition, completion_map[request.scene_id])
        outcome = _outcome_from_status(turn.status)
        return DialogueSceneTurnExecutionResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            outcome=outcome,
            response_mode=_response_mode_from_outcome(outcome),
            turn_result=turn,
            gate_check=gate_check,
            scene_state_before=scene_before,
            scene_state_after=scene_after,
            runtime_before=runtime_state,
            runtime_after=working_state,
        )

    provided_slot_names = {slot.slot_name for slot in request.provided_slots}
    missing = tuple(
        slot.slot_name
        for slot in scene_state.required_slots
        if slot.required and slot.slot_name not in provided_slot_names
    )
    if missing:
        repair_mode = _repair_mode_for_trigger(scene_state, "missing_slot")
        turn = DialogueTurnResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            intent_id=request.intent_id,
            status="repair",
            code="missing_required_slots",
            missing_required_slots=missing,
            repair_response_mode=repair_mode,
            summary_check_passed=None,
            unlock_outputs=_empty_unlocks(),
        )
        scene_after = _state_with_scene_state(definition, completion_map[request.scene_id])
        outcome = _outcome_from_status(turn.status)
        return DialogueSceneTurnExecutionResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            outcome=outcome,
            response_mode=_response_mode_from_outcome(outcome),
            turn_result=turn,
            gate_check=gate_check,
            scene_state_before=scene_before,
            scene_state_after=scene_after,
            runtime_before=runtime_state,
            runtime_after=working_state,
        )

    known_facts = _known_fact_pool(working_state, context)
    if any(fact_id not in known_facts for fact_id in request.presented_fact_ids):
        turn = DialogueTurnResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            intent_id=request.intent_id,
            status="refused",
            code="presented_fact_not_known",
            unlock_outputs=_empty_unlocks(),
        )
        scene_after = _state_with_scene_state(definition, completion_map[request.scene_id])
        outcome = _outcome_from_status(turn.status)
        return DialogueSceneTurnExecutionResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            outcome=outcome,
            response_mode=_response_mode_from_outcome(outcome),
            turn_result=turn,
            gate_check=gate_check,
            scene_state_before=scene_before,
            scene_state_after=scene_after,
            runtime_before=runtime_state,
            runtime_after=working_state,
        )

    known_evidence = set(context.known_evidence_ids)
    if any(evidence_id not in known_evidence for evidence_id in request.presented_evidence_ids):
        turn = DialogueTurnResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            intent_id=request.intent_id,
            status="refused",
            code="presented_evidence_not_known",
            unlock_outputs=_empty_unlocks(),
        )
        scene_after = _state_with_scene_state(definition, completion_map[request.scene_id])
        outcome = _outcome_from_status(turn.status)
        return DialogueSceneTurnExecutionResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            outcome=outcome,
            response_mode=_response_mode_from_outcome(outcome),
            turn_result=turn,
            gate_check=gate_check,
            scene_state_before=scene_before,
            scene_state_after=scene_after,
            runtime_before=runtime_state,
            runtime_after=working_state,
        )

    if request.intent_id == "present_evidence" and not request.presented_evidence_ids:
        repair_mode = _repair_mode_for_trigger(scene_state, "weak_evidence")
        turn = DialogueTurnResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            intent_id=request.intent_id,
            status="repair",
            code="missing_evidence_reference",
            repair_response_mode=repair_mode,
            unlock_outputs=_empty_unlocks(),
        )
        scene_after = _state_with_scene_state(definition, completion_map[request.scene_id])
        outcome = _outcome_from_status(turn.status)
        return DialogueSceneTurnExecutionResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            outcome=outcome,
            response_mode=_response_mode_from_outcome(outcome),
            turn_result=turn,
            gate_check=gate_check,
            scene_state_before=scene_before,
            scene_state_after=scene_after,
            runtime_before=runtime_state,
            runtime_after=working_state,
        )

    if request.intent_id == "challenge_contradiction" and len(request.presented_fact_ids) < 2:
        repair_mode = _repair_mode_for_trigger(scene_state, "weak_evidence")
        turn = DialogueTurnResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            intent_id=request.intent_id,
            status="repair",
            code="insufficient_contradiction_facts",
            repair_response_mode=repair_mode,
            unlock_outputs=_empty_unlocks(),
        )
        scene_after = _state_with_scene_state(definition, completion_map[request.scene_id])
        outcome = _outcome_from_status(turn.status)
        return DialogueSceneTurnExecutionResult(
            scene_id=request.scene_id,
            npc_id=request.npc_id,
            outcome=outcome,
            response_mode=_response_mode_from_outcome(outcome),
            turn_result=turn,
            gate_check=gate_check,
            scene_state_before=scene_before,
            scene_state_after=scene_after,
            runtime_before=runtime_state,
            runtime_after=working_state,
        )

    summary_check_passed: bool | None = None
    unlock_outputs = _empty_unlocks()
    revealed_fact_ids: tuple[str, ...] = ()
    new_completion = completion_map[request.scene_id]
    new_active_scene = working_state.active_scene_id
    code = "turn_accepted"

    if request.intent_id == "summarize_understanding":
        summary_count = len(
            {
                fact_id
                for fact_id in request.presented_fact_ids
                if fact_id in known_facts and fact_id in set(scene_state.allowed_fact_ids)
            }
        )
        summary_check_passed = summary_count >= scene_state.summary_requirement.min_fact_count
        if not summary_check_passed:
            repair_mode = _repair_mode_for_trigger(scene_state, "weak_evidence")
            turn = DialogueTurnResult(
                scene_id=request.scene_id,
                npc_id=request.npc_id,
                intent_id=request.intent_id,
                status="repair",
                code="summary_insufficient_facts",
                repair_response_mode=repair_mode,
                summary_check_passed=False,
                unlock_outputs=_empty_unlocks(),
            )
            scene_after = _state_with_scene_state(definition, completion_map[request.scene_id])
            outcome = _outcome_from_status(turn.status)
            return DialogueSceneTurnExecutionResult(
                scene_id=request.scene_id,
                npc_id=request.npc_id,
                outcome=outcome,
                response_mode=_response_mode_from_outcome(outcome),
                turn_result=turn,
                gate_check=gate_check,
                scene_state_before=scene_before,
                scene_state_after=scene_after,
                runtime_before=runtime_state,
                runtime_after=working_state,
            )
        unlock_outputs = scene_state.unlock_outputs
        revealed_fact_ids = tuple(sorted(scene_state.unlock_outputs.new_fact_ids))
        new_completion = "completed"
        new_active_scene = None
        code = "scene_completed"
    elif request.intent_id == "goodbye":
        new_completion = "available"
        new_active_scene = None
        code = "scene_paused"

    trust_delta, stress_delta = _intent_affect(request.intent_id, "accepted")
    turn = DialogueTurnResult(
        scene_id=request.scene_id,
        npc_id=request.npc_id,
        intent_id=request.intent_id,
        status="accepted",
        code=code,
        revealed_fact_ids=revealed_fact_ids,
        trust_delta=trust_delta,
        stress_delta=stress_delta,
        missing_required_slots=(),
        repair_response_mode=None,
        summary_check_passed=summary_check_passed,
        unlock_outputs=unlock_outputs,
    )

    updated_completion_map = dict(completion_map)
    updated_completion_map[request.scene_id] = new_completion
    updated_revealed = tuple(sorted(set(working_state.revealed_fact_ids).union(revealed_fact_ids)))
    surfaced = set(working_state.surfaced_scene_ids).union(unlock_outputs.new_scene_ids)
    if unlock_outputs.new_scene_ids:
        for scene_id in unlock_outputs.new_scene_ids:
            if updated_completion_map[scene_id] == "locked":
                updated_completion_map[scene_id] = "available"

    runtime_after = DialogueSceneRuntimeState(
        scene_definitions=working_state.scene_definitions,
        scene_completion_states=tuple((sid, updated_completion_map[sid]) for sid in _SCENE_ORDER),
        active_scene_id=new_active_scene,
        revealed_fact_ids=updated_revealed,
        emitted_scene_completion_flags=tuple(
            sorted(set(working_state.emitted_scene_completion_flags).union(unlock_outputs.scene_completion_flags))
        ),
        emitted_object_action_unlocks=tuple(
            sorted(set(working_state.emitted_object_action_unlocks).union(unlock_outputs.new_object_actions))
        ),
        surfaced_scene_ids=tuple(scene_id for scene_id in _SCENE_ORDER if scene_id in surfaced),
        turn_index=working_state.turn_index + 1,
    )

    scene_after = _state_with_scene_state(definition, updated_completion_map[request.scene_id])
    outcome = _outcome_from_status(turn.status)
    return DialogueSceneTurnExecutionResult(
        scene_id=request.scene_id,
        npc_id=request.npc_id,
        outcome=outcome,
        response_mode=_response_mode_from_outcome(outcome),
        turn_result=turn,
        gate_check=gate_check,
        scene_state_before=scene_before,
        scene_state_after=scene_after,
        runtime_before=runtime_state,
        runtime_after=runtime_after,
    )


def apply_dialogue_turn_to_progress(
    progress: InvestigationProgressState,
    turn_result: DialogueSceneTurnExecutionResult,
) -> InvestigationProgressState:
    """Project deterministic dialogue fact reveals into investigation progress."""
    known_facts = set(progress.known_fact_ids).union(turn_result.turn_result.revealed_fact_ids)
    return InvestigationProgressState(
        discovered_evidence_ids=progress.discovered_evidence_ids,
        collected_evidence_ids=progress.collected_evidence_ids,
        observed_clue_ids=progress.observed_clue_ids,
        known_fact_ids=tuple(sorted(known_facts)),
        unlockable_contradiction_edge_ids=progress.unlockable_contradiction_edge_ids,
        known_contradiction_edge_ids=progress.known_contradiction_edge_ids,
        consumed_action_keys=progress.consumed_action_keys,
        satisfied_action_flags=progress.satisfied_action_flags,
    )


__all__ = [
    "DialogueExecutionContext",
    "DialogueSceneEnterResult",
    "DialogueSceneRuntimeState",
    "DialogueSceneTurnExecutionResult",
    "SceneEntryStatus",
    "SceneGateCheckResult",
    "SceneRuntimeOutcome",
    "apply_dialogue_turn_to_progress",
    "build_dialogue_execution_context",
    "build_initial_dialogue_scene_runtime",
    "enter_dialogue_scene",
    "execute_dialogue_turn",
]
