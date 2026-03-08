from __future__ import annotations

"""Deterministic safe-context packaging for optional dialogue adapters (Phase 8B).

This module assembles legal per-turn adapter context from deterministic runtime
state. It is presentation-facing only and must not become gameplay logic.

Safety rules enforced here:
- include only currently visible and scene-legal fact content
- exclude hidden/unrevealed fact ids and text
- exclude future scene outcomes and internal resolution internals
"""

from dataclasses import dataclass

from .cast_registry import IdentityRole, get_cast_entry
from .dialogue_adapter import (
    DialogueAdapterFactPayload,
    DialogueAdapterInput,
    DialogueAdapterLearningView,
    DialogueAdapterVisibleNPCState,
    build_dialogue_adapter_input,
)
from .dialogue_domain import DialogueIntentId, DialogueSlotName, DialogueTurnStatus
from .dialogue_runtime import DialogueSceneTurnExecutionResult, SceneRuntimeOutcome
from .learning_state import LearningState
from .models import CaseState, SceneCompletionState, SceneId
from .npc_state import NPCState


def _sorted_unique(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(sorted({value for value in values if isinstance(value, str) and value}))


@dataclass(frozen=True)
class DialogueAdapterNPCIdentityBasics:
    npc_id: str
    display_name: str
    identity_role: IdentityRole
    baseline_register: str
    tell_profile: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.npc_id:
            raise ValueError("DialogueAdapterNPCIdentityBasics.npc_id must be non-empty")
        if not self.display_name:
            raise ValueError("DialogueAdapterNPCIdentityBasics.display_name must be non-empty")
        if not self.baseline_register:
            raise ValueError("DialogueAdapterNPCIdentityBasics.baseline_register must be non-empty")
        object.__setattr__(self, "tell_profile", _sorted_unique(self.tell_profile))


@dataclass(frozen=True)
class DialogueAdapterLegalFactSlice:
    visible_fact_ids: tuple[str, ...]
    newly_revealed_fact_ids: tuple[str, ...]
    visible_fact_payloads: tuple[DialogueAdapterFactPayload, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "visible_fact_ids", _sorted_unique(self.visible_fact_ids))
        object.__setattr__(self, "newly_revealed_fact_ids", _sorted_unique(self.newly_revealed_fact_ids))
        payload_ids = tuple(row.fact_id for row in self.visible_fact_payloads)
        if payload_ids != tuple(self.visible_fact_ids):
            raise ValueError(
                "DialogueAdapterLegalFactSlice.visible_fact_payloads must align one-to-one with visible_fact_ids"
            )
        if not set(self.newly_revealed_fact_ids).issubset(self.visible_fact_ids):
            raise ValueError(
                "DialogueAdapterLegalFactSlice.newly_revealed_fact_ids must be a subset of visible_fact_ids"
            )


@dataclass(frozen=True)
class DialogueAdapterTurnClassification:
    intent_id: DialogueIntentId
    turn_status: DialogueTurnStatus
    turn_code: str
    runtime_outcome: SceneRuntimeOutcome
    runtime_response_mode: str
    repair_response_mode: str | None
    trust_delta: float
    stress_delta: float
    missing_required_slots: tuple[DialogueSlotName, ...]
    summary_check_code: str | None
    summary_check_passed: bool | None

    def __post_init__(self) -> None:
        if not self.turn_code:
            raise ValueError("DialogueAdapterTurnClassification.turn_code must be non-empty")
        object.__setattr__(self, "missing_required_slots", tuple(sorted(set(self.missing_required_slots))))


@dataclass(frozen=True)
class DialogueAdapterContextPackage:
    case_id: str
    seed: str
    scene_id: SceneId
    turn_index: int
    active_scene_id: SceneId | None
    scene_completion_state: SceneCompletionState
    npc_identity: DialogueAdapterNPCIdentityBasics
    visible_npc_state: DialogueAdapterVisibleNPCState | None
    legal_facts: DialogueAdapterLegalFactSlice
    turn: DialogueAdapterTurnClassification
    allowed_intents: tuple[DialogueIntentId, ...]
    learning_view: DialogueAdapterLearningView | None

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("DialogueAdapterContextPackage.case_id must be non-empty")
        if not self.seed:
            raise ValueError("DialogueAdapterContextPackage.seed must be non-empty")
        if self.turn_index < 0:
            raise ValueError("DialogueAdapterContextPackage.turn_index must be >= 0")
        object.__setattr__(self, "allowed_intents", tuple(self.allowed_intents))


@dataclass(frozen=True)
class DialogueAdapterPromptContext:
    guardrails: tuple[str, ...]
    scene_header: str
    npc_header: str
    turn_header: str
    legal_fact_lines: tuple[str, ...]
    learning_lines: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "guardrails", _sorted_unique(self.guardrails))
        object.__setattr__(self, "legal_fact_lines", tuple(self.legal_fact_lines))
        object.__setattr__(self, "learning_lines", tuple(self.learning_lines))
        if not self.scene_header or not self.npc_header or not self.turn_header:
            raise ValueError("DialogueAdapterPromptContext headers must be non-empty")


def build_safe_dialogue_adapter_context(payload: DialogueAdapterInput) -> DialogueAdapterContextPackage:
    """Assemble legal adapter context from one deterministic adapter payload."""

    cast_entry = get_cast_entry(payload.npc_id)
    npc_identity = DialogueAdapterNPCIdentityBasics(
        npc_id=cast_entry.npc_id,
        display_name=cast_entry.display_name,
        identity_role=cast_entry.identity_role,
        baseline_register=cast_entry.baseline_register,
        tell_profile=cast_entry.tell_profile,
    )

    legal_visible_ids = tuple(
        sorted(
            set(payload.visible_fact_ids)
            .union(payload.turn_revealed_fact_ids)
            .intersection(payload.allowed_fact_ids)
        )
    )
    newly_revealed_ids = tuple(sorted(set(payload.turn_revealed_fact_ids).intersection(legal_visible_ids)))

    payload_by_id = {row.fact_id: row for row in payload.allowed_fact_payloads}
    legal_payloads: list[DialogueAdapterFactPayload] = []
    for fact_id in legal_visible_ids:
        row = payload_by_id.get(fact_id)
        if row is None:
            raise ValueError(
                f"Missing fact payload for legal visible fact {fact_id!r}; payload must stay scene-contract aligned"
            )
        if not row.currently_revealed:
            raise ValueError(
                f"Fact payload {fact_id!r} is not currently revealed and must not be packaged"
            )
        legal_payloads.append(row)

    return DialogueAdapterContextPackage(
        case_id=payload.case_id,
        seed=payload.seed,
        scene_id=payload.scene_id,
        turn_index=payload.turn_index,
        active_scene_id=payload.active_scene_id,
        scene_completion_state=payload.scene_completion_state,
        npc_identity=npc_identity,
        visible_npc_state=payload.visible_npc_state,
        legal_facts=DialogueAdapterLegalFactSlice(
            visible_fact_ids=legal_visible_ids,
            newly_revealed_fact_ids=newly_revealed_ids,
            visible_fact_payloads=tuple(legal_payloads),
        ),
        turn=DialogueAdapterTurnClassification(
            intent_id=payload.intent_id,
            turn_status=payload.turn_status,
            turn_code=payload.turn_code,
            runtime_outcome=payload.runtime_outcome,
            runtime_response_mode=payload.runtime_response_mode,
            repair_response_mode=payload.repair_response_mode,
            trust_delta=payload.trust_delta,
            stress_delta=payload.stress_delta,
            missing_required_slots=payload.missing_required_slots,
            summary_check_code=payload.summary_check_code,
            summary_check_passed=payload.summary_check_passed,
        ),
        allowed_intents=payload.allowed_intents,
        learning_view=payload.learning_view,
    )


def build_safe_dialogue_adapter_context_from_turn(
    *,
    case_state: CaseState,
    turn: DialogueSceneTurnExecutionResult,
    visible_npc_state: NPCState | None = None,
    learning_state: LearningState | None = None,
) -> DialogueAdapterContextPackage:
    """Compose Phase 8A payload build + Phase 8B legal packaging."""

    payload = build_dialogue_adapter_input(
        case_state=case_state,
        turn=turn,
        visible_npc_state=visible_npc_state,
        learning_state=learning_state,
    )
    return build_safe_dialogue_adapter_context(payload)


def build_dialogue_adapter_prompt_context(
    package: DialogueAdapterContextPackage,
) -> DialogueAdapterPromptContext:
    """Build narrow, factual prompt-ready context text sections."""

    guardrails = (
        "do_not_invent_facts",
        "do_not_change_scene_progress",
        "use_only_visible_legal_facts",
        "do_not_predict_future_outcomes",
    )
    scene_header = (
        f"scene={package.scene_id} active_scene={package.active_scene_id} "
        f"completion={package.scene_completion_state}"
    )
    npc_header = (
        f"npc={package.npc_identity.display_name} role={package.npc_identity.identity_role} "
        f"register={package.npc_identity.baseline_register}"
    )
    turn_header = (
        f"intent={package.turn.intent_id} status={package.turn.turn_status} code={package.turn.turn_code} "
        f"response_mode={package.turn.runtime_response_mode}"
    )

    legal_fact_lines = tuple(
        f"{row.fact_id}:{row.text}"
        for row in package.legal_facts.visible_fact_payloads
    )

    learning_lines: list[str] = []
    if package.learning_view is not None:
        learning_lines = [
            f"difficulty={package.learning_view.difficulty_profile}",
            f"hint={package.learning_view.current_hint_level}",
            f"recommended_hint={package.learning_view.recommended_hint_level}",
            f"summary_strictness={package.learning_view.summary_strictness}",
            f"english_meta_allowed={package.learning_view.english_meta_allowed}",
            f"french_action_required={package.learning_view.french_action_required}",
        ]

    return DialogueAdapterPromptContext(
        guardrails=guardrails,
        scene_header=scene_header,
        npc_header=npc_header,
        turn_header=turn_header,
        legal_fact_lines=legal_fact_lines,
        learning_lines=tuple(learning_lines),
    )


__all__ = [
    "DialogueAdapterContextPackage",
    "DialogueAdapterLegalFactSlice",
    "DialogueAdapterNPCIdentityBasics",
    "DialogueAdapterPromptContext",
    "DialogueAdapterTurnClassification",
    "build_dialogue_adapter_prompt_context",
    "build_safe_dialogue_adapter_context",
    "build_safe_dialogue_adapter_context_from_turn",
]

