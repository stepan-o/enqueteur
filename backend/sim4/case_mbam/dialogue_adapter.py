from __future__ import annotations

"""Optional LLM dialogue presentation adapter contract (Phase 8A).

This module defines a narrow boundary for optional dialogue phrasing adapters.
Deterministic scene execution remains canonical source of truth.

Hard boundary:
- Input contains only already-determined legal scene/runtime truth slices.
- Output can phrase text only; it may not mutate facts, gates, or progression.
- Any fact references in output must stay within visible/revealed legal facts.
"""

from dataclasses import dataclass
import re
from typing import Literal, Protocol, runtime_checkable

from .dialogue_domain import DialogueIntentId, DialogueSlotName, DialogueTurnStatus
from .dialogue_runtime import DialogueSceneTurnExecutionResult, SceneRuntimeOutcome
from .learning_state import LearningHintLevel, LearningState
from .models import CaseState, DifficultyProfile, SceneCompletionState, SceneId, TruthNodeType, TruthVisibility
from .npc_state import NPCState, NpcAvailability, NpcEmotion, NpcInteractionMode, NpcSoftAlignmentHint, NpcStance, NpcTrustTrend


DialogueAdapterResponseMode = Literal["accept", "block", "repair", "reject"]
_FACT_ID_TOKEN_RE = re.compile(r"\bN\d+\b", re.IGNORECASE)
_SAFE_SOURCE_TOKEN_RE = re.compile(r"^[a-z0-9_]{1,40}$")


def _sorted_unique(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(sorted({value for value in values if isinstance(value, str) and value}))


def _extract_fact_id_mentions(values: tuple[str | None, ...]) -> tuple[str, ...]:
    out: set[str] = set()
    for value in values:
        if value is None:
            continue
        for match in _FACT_ID_TOKEN_RE.findall(value):
            out.add(match.upper())
    return tuple(sorted(out))


@dataclass(frozen=True)
class DialogueAdapterFactPayload:
    fact_id: str
    fact_type: TruthNodeType
    text: str
    visibility: TruthVisibility
    source_ids: tuple[str, ...]
    unlock_conditions: tuple[str, ...]
    currently_revealed: bool

    def __post_init__(self) -> None:
        if not self.fact_id:
            raise ValueError("DialogueAdapterFactPayload.fact_id must be non-empty")
        if not self.text:
            raise ValueError("DialogueAdapterFactPayload.text must be non-empty")
        object.__setattr__(self, "source_ids", _sorted_unique(self.source_ids))
        object.__setattr__(self, "unlock_conditions", _sorted_unique(self.unlock_conditions))


@dataclass(frozen=True)
class DialogueAdapterVisibleNPCState:
    npc_id: str
    current_room_id: str
    availability: NpcAvailability
    trust: float
    stress: float
    stance: NpcStance
    emotion: NpcEmotion
    soft_alignment_hint: NpcSoftAlignmentHint
    portrait_variant: str
    tell_cue: str | None
    suggested_interaction_mode: NpcInteractionMode
    trust_trend: NpcTrustTrend

    def __post_init__(self) -> None:
        if not self.npc_id:
            raise ValueError("DialogueAdapterVisibleNPCState.npc_id must be non-empty")
        if not self.current_room_id:
            raise ValueError("DialogueAdapterVisibleNPCState.current_room_id must be non-empty")
        if not (0.0 <= self.trust <= 1.0):
            raise ValueError("DialogueAdapterVisibleNPCState.trust must be in [0.0, 1.0]")
        if not (0.0 <= self.stress <= 1.0):
            raise ValueError("DialogueAdapterVisibleNPCState.stress must be in [0.0, 1.0]")


@dataclass(frozen=True)
class DialogueAdapterLearningView:
    difficulty_profile: DifficultyProfile
    current_hint_level: LearningHintLevel
    recommended_hint_level: LearningHintLevel
    english_meta_allowed: bool
    french_action_required: bool
    summary_strictness: Literal["relaxed", "strict"]
    reason_code: str

    def __post_init__(self) -> None:
        if not self.reason_code:
            raise ValueError("DialogueAdapterLearningView.reason_code must be non-empty")


@dataclass(frozen=True)
class DialogueAdapterInput:
    case_id: str
    seed: str
    scene_id: SceneId
    npc_id: str
    turn_index: int
    active_scene_id: SceneId | None
    scene_completion_state: SceneCompletionState
    intent_id: DialogueIntentId
    turn_status: DialogueTurnStatus
    turn_code: str
    runtime_outcome: SceneRuntimeOutcome
    runtime_response_mode: DialogueAdapterResponseMode
    repair_response_mode: str | None
    trust_delta: float
    stress_delta: float
    missing_required_slots: tuple[DialogueSlotName, ...]
    allowed_intents: tuple[DialogueIntentId, ...]
    allowed_fact_ids: tuple[str, ...]
    allowed_fact_payloads: tuple[DialogueAdapterFactPayload, ...]
    visible_fact_ids: tuple[str, ...]
    turn_revealed_fact_ids: tuple[str, ...]
    unlock_scene_ids: tuple[SceneId, ...]
    unlock_object_actions: tuple[str, ...]
    unlock_completion_flags: tuple[str, ...]
    summary_check_code: str | None
    summary_check_passed: bool | None
    visible_npc_state: DialogueAdapterVisibleNPCState | None
    learning_view: DialogueAdapterLearningView | None

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("DialogueAdapterInput.case_id must be non-empty")
        if not self.seed:
            raise ValueError("DialogueAdapterInput.seed must be non-empty")
        if not self.npc_id:
            raise ValueError("DialogueAdapterInput.npc_id must be non-empty")
        if not self.turn_code:
            raise ValueError("DialogueAdapterInput.turn_code must be non-empty")
        if self.turn_index < 0:
            raise ValueError("DialogueAdapterInput.turn_index must be >= 0")
        if self.runtime_response_mode not in {"accept", "block", "repair", "reject"}:
            raise ValueError("DialogueAdapterInput.runtime_response_mode must be a supported mode")
        object.__setattr__(self, "missing_required_slots", tuple(sorted(set(self.missing_required_slots))))
        object.__setattr__(self, "allowed_fact_ids", _sorted_unique(self.allowed_fact_ids))
        object.__setattr__(self, "visible_fact_ids", _sorted_unique(self.visible_fact_ids))
        object.__setattr__(self, "turn_revealed_fact_ids", _sorted_unique(self.turn_revealed_fact_ids))
        object.__setattr__(self, "unlock_object_actions", _sorted_unique(self.unlock_object_actions))
        object.__setattr__(self, "unlock_completion_flags", _sorted_unique(self.unlock_completion_flags))
        object.__setattr__(self, "allowed_intents", tuple(self.allowed_intents))
        object.__setattr__(self, "unlock_scene_ids", tuple(self.unlock_scene_ids))


@dataclass(frozen=True)
class DialogueAdapterOutput:
    npc_utterance_text: str
    short_rephrase_line: str | None = None
    hint_line: str | None = None
    summary_prompt_line: str | None = None
    response_mode_metadata: tuple[str, ...] = ()
    referenced_fact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.npc_utterance_text:
            raise ValueError("DialogueAdapterOutput.npc_utterance_text must be non-empty")
        object.__setattr__(self, "response_mode_metadata", _sorted_unique(self.response_mode_metadata))
        object.__setattr__(self, "referenced_fact_ids", _sorted_unique(self.referenced_fact_ids))


@runtime_checkable
class OptionalDialoguePresentationAdapter(Protocol):
    """Adapter protocol for optional LLM-backed dialogue presentation."""

    def render_turn(self, payload: DialogueAdapterInput) -> DialogueAdapterOutput: ...


def _to_visible_npc_state(state: NPCState) -> DialogueAdapterVisibleNPCState:
    return DialogueAdapterVisibleNPCState(
        npc_id=state.npc_id,
        current_room_id=state.current_room_id,
        availability=state.availability,
        trust=state.trust,
        stress=state.stress,
        stance=state.stance,
        emotion=state.emotion,
        soft_alignment_hint=state.soft_alignment_hint,
        portrait_variant=state.card_state.portrait_variant,
        tell_cue=state.card_state.tell_cue,
        suggested_interaction_mode=state.card_state.suggested_interaction_mode,
        trust_trend=state.card_state.trust_trend,
    )


def _to_learning_view(state: LearningState) -> DialogueAdapterLearningView:
    return DialogueAdapterLearningView(
        difficulty_profile=state.difficulty_profile,
        current_hint_level=state.current_hint_level,
        recommended_hint_level=state.scaffolding_policy.recommended_mode,
        english_meta_allowed=state.scaffolding_policy.english_meta_allowed,
        french_action_required=state.scaffolding_policy.french_action_required,
        summary_strictness=state.scaffolding_policy.summary_strictness,
        reason_code=state.scaffolding_policy.reason_code,
    )


def _build_allowed_fact_payloads(
    case_state: CaseState,
    *,
    allowed_fact_ids: tuple[str, ...],
    visible_fact_ids: tuple[str, ...],
) -> tuple[DialogueAdapterFactPayload, ...]:
    truth_nodes = {node.fact_id: node for node in case_state.truth_graph.nodes}
    visible = set(visible_fact_ids)
    payloads: list[DialogueAdapterFactPayload] = []
    for fact_id in allowed_fact_ids:
        node = truth_nodes.get(fact_id)
        if node is None:
            raise ValueError(f"Allowed scene fact not found in CaseState truth graph: {fact_id}")
        payloads.append(
            DialogueAdapterFactPayload(
                fact_id=node.fact_id,
                fact_type=node.type,
                text=node.text,
                visibility=node.visibility,
                source_ids=node.source_ids,
                unlock_conditions=node.unlock_conditions,
                currently_revealed=node.fact_id in visible,
            )
        )
    return tuple(payloads)


def build_dialogue_adapter_input(
    *,
    case_state: CaseState,
    turn: DialogueSceneTurnExecutionResult,
    visible_npc_state: NPCState | None = None,
    learning_state: LearningState | None = None,
) -> DialogueAdapterInput:
    """Build adapter input from deterministic scene runtime state.

    This function is the truth boundary:
    - reads deterministic runtime/case state
    - emits legal presentation payload only
    - does not mutate progression or truth
    """

    scene_state = turn.scene_state_after
    visible_fact_ids = tuple(turn.runtime_after.revealed_fact_ids)
    turn_revealed_fact_ids = tuple(turn.turn_result.revealed_fact_ids)
    allowed_fact_ids = tuple(scene_state.allowed_fact_ids)
    allowed_fact_payloads = _build_allowed_fact_payloads(
        case_state,
        allowed_fact_ids=allowed_fact_ids,
        visible_fact_ids=visible_fact_ids,
    )

    summary_check_code = turn.summary_check.code if turn.summary_check is not None else None
    if turn.summary_check is not None:
        summary_check_passed = turn.summary_check.passed
    else:
        summary_check_passed = turn.turn_result.summary_check_passed

    return DialogueAdapterInput(
        case_id=case_state.case_id,
        seed=case_state.seed,
        scene_id=turn.scene_id,
        npc_id=turn.npc_id,
        turn_index=turn.runtime_after.turn_index,
        active_scene_id=turn.runtime_after.active_scene_id,
        scene_completion_state=scene_state.completion_state,
        intent_id=turn.turn_result.intent_id,
        turn_status=turn.turn_result.status,
        turn_code=turn.turn_result.code,
        runtime_outcome=turn.outcome,
        runtime_response_mode=turn.response_mode,
        repair_response_mode=turn.turn_result.repair_response_mode,
        trust_delta=turn.turn_result.trust_delta,
        stress_delta=turn.turn_result.stress_delta,
        missing_required_slots=turn.turn_result.missing_required_slots,
        allowed_intents=scene_state.allowed_intents,
        allowed_fact_ids=allowed_fact_ids,
        allowed_fact_payloads=allowed_fact_payloads,
        visible_fact_ids=visible_fact_ids,
        turn_revealed_fact_ids=turn_revealed_fact_ids,
        unlock_scene_ids=turn.turn_result.unlock_outputs.new_scene_ids,
        unlock_object_actions=turn.turn_result.unlock_outputs.new_object_actions,
        unlock_completion_flags=turn.turn_result.unlock_outputs.scene_completion_flags,
        summary_check_code=summary_check_code,
        summary_check_passed=summary_check_passed,
        visible_npc_state=_to_visible_npc_state(visible_npc_state) if visible_npc_state is not None else None,
        learning_view=_to_learning_view(learning_state) if learning_state is not None else None,
    )


def validate_dialogue_adapter_output(output: DialogueAdapterOutput, payload: DialogueAdapterInput) -> None:
    """Validate adapter output against legal deterministic truth boundaries."""

    legal_fact_ids = set(payload.visible_fact_ids).union(payload.turn_revealed_fact_ids)
    leaked = sorted(fact_id for fact_id in output.referenced_fact_ids if fact_id not in legal_fact_ids)
    if leaked:
        raise ValueError(
            "DialogueAdapterOutput.referenced_fact_ids contains facts outside legal visible slice: "
            + ", ".join(leaked)
        )

    mentioned_fact_ids = _extract_fact_id_mentions(
        (
            output.npc_utterance_text,
            output.short_rephrase_line,
            output.hint_line,
            output.summary_prompt_line,
            *output.response_mode_metadata,
        )
    )
    leaked_mentions = sorted(fact_id for fact_id in mentioned_fact_ids if fact_id not in legal_fact_ids)
    if leaked_mentions:
        raise ValueError(
            "DialogueAdapterOutput text contains fact ids outside legal visible slice: "
            + ", ".join(leaked_mentions)
        )

    combined_text = " ".join(
        row
        for row in (
            output.npc_utterance_text,
            output.short_rephrase_line,
            output.hint_line,
            output.summary_prompt_line,
            *output.response_mode_metadata,
        )
        if row is not None
    ).lower()
    restricted_fact_rows = tuple(
        row
        for row in payload.allowed_fact_payloads
        if row.fact_id not in legal_fact_ids and row.text.strip()
    )
    leaked_fact_text_ids = tuple(
        sorted(
            row.fact_id
            for row in restricted_fact_rows
            if row.text.strip().lower() in combined_text
        )
    )
    if leaked_fact_text_ids:
        raise ValueError(
            "DialogueAdapterOutput text contains fact content outside legal visible slice: "
            + ", ".join(leaked_fact_text_ids)
        )

    seen_metadata_values: dict[str, str] = {}
    for token in output.response_mode_metadata:
        if ":" not in token:
            raise ValueError("DialogueAdapterOutput.response_mode_metadata contains malformed token")
        key, value = token.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            raise ValueError("DialogueAdapterOutput.response_mode_metadata contains empty value")
        prior = seen_metadata_values.get(key)
        if prior is not None and prior != value:
            raise ValueError(
                f"DialogueAdapterOutput.response_mode_metadata contains conflicting {key} values"
            )
        seen_metadata_values[key] = value

    if "mode" in seen_metadata_values and seen_metadata_values["mode"] != payload.runtime_response_mode:
        raise ValueError("DialogueAdapterOutput.response_mode_metadata mode conflicts with deterministic turn result")
    if "outcome" in seen_metadata_values and seen_metadata_values["outcome"] != payload.runtime_outcome:
        raise ValueError("DialogueAdapterOutput.response_mode_metadata outcome conflicts with deterministic turn result")
    if "status" in seen_metadata_values and seen_metadata_values["status"] != payload.turn_status:
        raise ValueError("DialogueAdapterOutput.response_mode_metadata status conflicts with deterministic turn result")
    if "npc" in seen_metadata_values and seen_metadata_values["npc"] != payload.npc_id:
        raise ValueError("DialogueAdapterOutput.response_mode_metadata npc conflicts with deterministic turn result")
    if "reason" in seen_metadata_values:
        raise ValueError("DialogueAdapterOutput.response_mode_metadata reason is reserved for deterministic fallback")
    if "source" in seen_metadata_values and _SAFE_SOURCE_TOKEN_RE.match(seen_metadata_values["source"]) is None:
        raise ValueError("DialogueAdapterOutput.response_mode_metadata source is invalid")


class DeterministicDialoguePresentationAdapter(OptionalDialoguePresentationAdapter):
    """Fallback adapter with deterministic templated phrasing only."""

    def render_turn(self, payload: DialogueAdapterInput) -> DialogueAdapterOutput:
        utterance = (
            f"[{payload.scene_id}/{payload.npc_id}] "
            f"{payload.turn_status}:{payload.turn_code}"
        )
        rephrase = None
        if payload.turn_status == "repair":
            mode = payload.repair_response_mode or "repair"
            rephrase = f"repair_mode:{mode}"

        hint = None
        if payload.learning_view is not None and payload.turn_status in {"repair", "blocked_gate"}:
            hint = f"hint_level:{payload.learning_view.current_hint_level}"

        summary_prompt = None
        if payload.summary_check_code in {
            "summary_required",
            "summary_needed",
            "summary_insufficient_facts",
            "summary_missing_key_fact",
        }:
            summary_prompt = "resume_en_francais"

        output = DialogueAdapterOutput(
            npc_utterance_text=utterance,
            short_rephrase_line=rephrase,
            hint_line=hint,
            summary_prompt_line=summary_prompt,
            response_mode_metadata=(f"mode:{payload.runtime_response_mode}", f"outcome:{payload.runtime_outcome}"),
            referenced_fact_ids=tuple(payload.turn_revealed_fact_ids),
        )
        validate_dialogue_adapter_output(output, payload)
        return output


__all__ = [
    "DialogueAdapterFactPayload",
    "DialogueAdapterInput",
    "DialogueAdapterLearningView",
    "DialogueAdapterOutput",
    "DialogueAdapterResponseMode",
    "DialogueAdapterVisibleNPCState",
    "DeterministicDialoguePresentationAdapter",
    "OptionalDialoguePresentationAdapter",
    "build_dialogue_adapter_input",
    "validate_dialogue_adapter_output",
]
