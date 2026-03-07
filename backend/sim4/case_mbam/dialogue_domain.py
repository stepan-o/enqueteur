from __future__ import annotations

"""Deterministic MBAM dialogue-domain models and intent catalog (Phase 4A).

This module defines the canonical backend structures for structured dialogue
scenes S1..S5. It is intentionally model-only: no freeform parsing, no live
LLM behavior, and no scene execution runtime in this phase.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

from .models import SceneCompletionState, SceneId


DialogueIntentId = Literal[
    "ask_what_happened",
    "ask_when",
    "ask_where",
    "ask_who",
    "ask_what_seen",
    "request_access",
    "request_permission",
    "present_evidence",
    "challenge_contradiction",
    "summarize_understanding",
    "accuse",
    "reassure",
    "goodbye",
]

DialogueSlotName = Literal["time", "location", "item", "person", "reason"]

DialogueTrustGateFailureMode = Literal["deny", "deflect", "delay"]
DialogueStressGateFailureMode = Literal["shut_down", "evade", "switch_register"]

RepairTrigger = Literal["missing_slot", "wrong_register", "too_aggressive", "weak_evidence"]
RepairResponseMode = Literal["sentence_stem", "rephrase_choice", "meta_hint", "alternate_path"]

SummaryTargetLanguage = Literal["fr"]

DialogueTurnStatus = Literal[
    "accepted",
    "blocked_gate",
    "repair",
    "refused",
    "invalid_intent",
    "invalid_scene_state",
]

DialogueIntentCategory = Literal[
    "question",
    "request",
    "presentation",
    "challenge",
    "summary",
    "social",
    "closure",
]


MBAM_DIALOGUE_SCENE_IDS: tuple[SceneId, ...] = ("S1", "S2", "S3", "S4", "S5")


def _tupleize_strings(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    out = tuple(values)
    for value in out:
        if not isinstance(value, str) or not value:
            raise ValueError("Expected non-empty string values")
    return out


def _tupleize_scene_ids(values: tuple[SceneId, ...] | list[SceneId] | None) -> tuple[SceneId, ...]:
    if values is None:
        return ()
    out = tuple(values)
    for scene_id in out:
        if scene_id not in MBAM_DIALOGUE_SCENE_IDS:
            raise ValueError(f"Unknown SceneId: {scene_id!r}")
    return out


def _tupleize_intents(values: tuple[DialogueIntentId, ...] | list[DialogueIntentId] | None) -> tuple[DialogueIntentId, ...]:
    if values is None:
        return ()
    out = tuple(values)
    for intent in out:
        if intent not in _INTENT_BY_ID:
            raise ValueError(f"Unknown DialogueIntentId: {intent!r}")
    return out


def _tupleize_slot_names(values: tuple[DialogueSlotName, ...] | list[DialogueSlotName] | None) -> tuple[DialogueSlotName, ...]:
    if values is None:
        return ()
    out = tuple(values)
    for slot_name in out:
        if slot_name not in {"time", "location", "item", "person", "reason"}:
            raise ValueError(f"Unknown DialogueSlotName: {slot_name!r}")
    return out


@dataclass(frozen=True)
class DialogueSlotDescriptor:
    slot_name: DialogueSlotName
    required: bool = True


@dataclass(frozen=True)
class DialogueTrustGate:
    minimum_value: float | None = None
    failure_mode: DialogueTrustGateFailureMode = "deny"

    def __post_init__(self) -> None:
        if self.minimum_value is None:
            return
        if not (0.0 <= self.minimum_value <= 1.0):
            raise ValueError("DialogueTrustGate.minimum_value must be in [0.0, 1.0]")


@dataclass(frozen=True)
class DialogueStressGate:
    maximum_value: float | None = None
    failure_mode: DialogueStressGateFailureMode = "evade"

    def __post_init__(self) -> None:
        if self.maximum_value is None:
            return
        if not (0.0 <= self.maximum_value <= 1.0):
            raise ValueError("DialogueStressGate.maximum_value must be in [0.0, 1.0]")


@dataclass(frozen=True)
class DialogueRepairPath:
    repair_id: str
    trigger: RepairTrigger
    response_mode: RepairResponseMode

    def __post_init__(self) -> None:
        if not self.repair_id:
            raise ValueError("DialogueRepairPath.repair_id must be non-empty")


@dataclass(frozen=True)
class DialogueSummaryRequirement:
    required: bool = True
    min_fact_count: int = 1
    target_language: SummaryTargetLanguage = "fr"

    def __post_init__(self) -> None:
        if self.min_fact_count < 0:
            raise ValueError("DialogueSummaryRequirement.min_fact_count must be >= 0")
        if self.required and self.min_fact_count < 1:
            raise ValueError("DialogueSummaryRequirement.min_fact_count must be >= 1 when required=True")


@dataclass(frozen=True)
class DialogueUnlockOutputs:
    scene_completion_flags: tuple[str, ...] = ()
    new_fact_ids: tuple[str, ...] = ()
    new_object_actions: tuple[str, ...] = ()
    new_scene_ids: tuple[SceneId, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "scene_completion_flags", _tupleize_strings(self.scene_completion_flags))
        object.__setattr__(self, "new_fact_ids", _tupleize_strings(self.new_fact_ids))
        object.__setattr__(self, "new_object_actions", _tupleize_strings(self.new_object_actions))
        object.__setattr__(self, "new_scene_ids", _tupleize_scene_ids(self.new_scene_ids))


@dataclass(frozen=True)
class DialogueSceneState:
    scene_id: SceneId
    npc_id: str
    allowed_intents: tuple[DialogueIntentId, ...]
    required_slots: tuple[DialogueSlotDescriptor, ...] = ()
    allowed_fact_ids: tuple[str, ...] = ()
    revealed_fact_ids: tuple[str, ...] = ()
    trust_gate: DialogueTrustGate = field(default_factory=DialogueTrustGate)
    stress_gate: DialogueStressGate = field(default_factory=DialogueStressGate)
    repair_paths: tuple[DialogueRepairPath, ...] = ()
    summary_requirement: DialogueSummaryRequirement = field(default_factory=DialogueSummaryRequirement)
    unlock_outputs: DialogueUnlockOutputs = field(default_factory=DialogueUnlockOutputs)
    completion_state: SceneCompletionState = "locked"

    def __post_init__(self) -> None:
        if self.scene_id not in MBAM_DIALOGUE_SCENE_IDS:
            raise ValueError(f"Unknown scene_id: {self.scene_id!r}")
        if not self.npc_id:
            raise ValueError("DialogueSceneState.npc_id must be non-empty")

        object.__setattr__(self, "allowed_intents", _tupleize_intents(self.allowed_intents))
        object.__setattr__(self, "allowed_fact_ids", _tupleize_strings(self.allowed_fact_ids))
        object.__setattr__(self, "revealed_fact_ids", _tupleize_strings(self.revealed_fact_ids))

        if len(self.allowed_intents) != len(set(self.allowed_intents)):
            raise ValueError("DialogueSceneState.allowed_intents contains duplicates")
        if not self.allowed_intents:
            raise ValueError("DialogueSceneState.allowed_intents must be non-empty")

        slot_names = tuple(slot.slot_name for slot in self.required_slots)
        if len(slot_names) != len(set(slot_names)):
            raise ValueError("DialogueSceneState.required_slots contains duplicate slot_name values")

        allowed_fact_set = set(self.allowed_fact_ids)
        for fact_id in self.revealed_fact_ids:
            if fact_id not in allowed_fact_set:
                raise ValueError(
                    "DialogueSceneState.revealed_fact_ids must be a subset of allowed_fact_ids"
                )


@dataclass(frozen=True)
class DialogueIntentDefinition:
    intent_id: DialogueIntentId
    category: DialogueIntentCategory
    description: str
    required_slot_names: tuple[DialogueSlotName, ...] = ()
    optional_slot_names: tuple[DialogueSlotName, ...] = ()
    may_present_evidence: bool = False
    may_present_facts: bool = False

    def __post_init__(self) -> None:
        if not self.description:
            raise ValueError("DialogueIntentDefinition.description must be non-empty")
        object.__setattr__(self, "required_slot_names", _tupleize_slot_names(self.required_slot_names))
        object.__setattr__(self, "optional_slot_names", _tupleize_slot_names(self.optional_slot_names))
        overlap = set(self.required_slot_names).intersection(self.optional_slot_names)
        if overlap:
            raise ValueError(f"Intent slot names cannot be both required and optional: {sorted(overlap)}")


@dataclass(frozen=True)
class DialogueTurnSlotValue:
    slot_name: DialogueSlotName
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("DialogueTurnSlotValue.value must be non-empty")


@dataclass(frozen=True)
class DialogueTurnRequest:
    scene_id: SceneId
    npc_id: str
    intent_id: DialogueIntentId
    provided_slots: tuple[DialogueTurnSlotValue, ...] = ()
    presented_fact_ids: tuple[str, ...] = ()
    presented_evidence_ids: tuple[str, ...] = ()
    utterance_text: str | None = None

    def __post_init__(self) -> None:
        if self.scene_id not in MBAM_DIALOGUE_SCENE_IDS:
            raise ValueError(f"Unknown scene_id: {self.scene_id!r}")
        if not self.npc_id:
            raise ValueError("DialogueTurnRequest.npc_id must be non-empty")
        if self.intent_id not in _INTENT_BY_ID:
            raise ValueError(f"Unknown intent_id: {self.intent_id!r}")

        object.__setattr__(self, "presented_fact_ids", _tupleize_strings(self.presented_fact_ids))
        object.__setattr__(self, "presented_evidence_ids", _tupleize_strings(self.presented_evidence_ids))


@dataclass(frozen=True)
class DialogueTurnResult:
    scene_id: SceneId
    npc_id: str
    intent_id: DialogueIntentId
    status: DialogueTurnStatus
    code: str
    revealed_fact_ids: tuple[str, ...] = ()
    trust_delta: float = 0.0
    stress_delta: float = 0.0
    missing_required_slots: tuple[DialogueSlotName, ...] = ()
    repair_response_mode: RepairResponseMode | None = None
    summary_check_passed: bool | None = None
    unlock_outputs: DialogueUnlockOutputs = field(default_factory=DialogueUnlockOutputs)

    def __post_init__(self) -> None:
        if self.scene_id not in MBAM_DIALOGUE_SCENE_IDS:
            raise ValueError(f"Unknown scene_id: {self.scene_id!r}")
        if not self.npc_id:
            raise ValueError("DialogueTurnResult.npc_id must be non-empty")
        if self.intent_id not in _INTENT_BY_ID:
            raise ValueError(f"Unknown intent_id: {self.intent_id!r}")
        if not self.code:
            raise ValueError("DialogueTurnResult.code must be non-empty")

        object.__setattr__(self, "revealed_fact_ids", _tupleize_strings(self.revealed_fact_ids))
        object.__setattr__(self, "missing_required_slots", _tupleize_slot_names(self.missing_required_slots))

        if not (-1.0 <= self.trust_delta <= 1.0):
            raise ValueError("DialogueTurnResult.trust_delta must be in [-1.0, 1.0]")
        if not (-1.0 <= self.stress_delta <= 1.0):
            raise ValueError("DialogueTurnResult.stress_delta must be in [-1.0, 1.0]")
        if self.status == "repair" and self.repair_response_mode is None:
            raise ValueError("DialogueTurnResult.repair_response_mode is required when status='repair'")


_INTENT_CATALOG: tuple[DialogueIntentDefinition, ...] = (
    DialogueIntentDefinition(
        intent_id="ask_what_happened",
        category="question",
        description="Ask for a broad account of what happened.",
    ),
    DialogueIntentDefinition(
        intent_id="ask_when",
        category="question",
        description="Ask for timeline or exact/relative time details.",
        optional_slot_names=("time",),
    ),
    DialogueIntentDefinition(
        intent_id="ask_where",
        category="question",
        description="Ask where an event, object, or person was located.",
        optional_slot_names=("location",),
    ),
    DialogueIntentDefinition(
        intent_id="ask_who",
        category="question",
        description="Ask who was present, involved, or seen.",
        optional_slot_names=("person",),
    ),
    DialogueIntentDefinition(
        intent_id="ask_what_seen",
        category="question",
        description="Ask what the witness/NPC directly observed.",
    ),
    DialogueIntentDefinition(
        intent_id="request_access",
        category="request",
        description="Request access to restricted area or system.",
        optional_slot_names=("reason",),
    ),
    DialogueIntentDefinition(
        intent_id="request_permission",
        category="request",
        description="Request permission for a sensitive action.",
        optional_slot_names=("reason",),
    ),
    DialogueIntentDefinition(
        intent_id="present_evidence",
        category="presentation",
        description="Present collected evidence to support inquiry.",
        required_slot_names=("item",),
        optional_slot_names=("reason",),
        may_present_evidence=True,
        may_present_facts=True,
    ),
    DialogueIntentDefinition(
        intent_id="challenge_contradiction",
        category="challenge",
        description="Challenge statement using contradiction logic.",
        optional_slot_names=("person", "time", "reason"),
        may_present_facts=True,
    ),
    DialogueIntentDefinition(
        intent_id="summarize_understanding",
        category="summary",
        description="Provide a structured recap of known facts.",
        optional_slot_names=("time", "location", "person", "reason"),
        may_present_facts=True,
    ),
    DialogueIntentDefinition(
        intent_id="accuse",
        category="challenge",
        description="Make a direct accusation with supporting rationale.",
        required_slot_names=("person", "reason"),
        may_present_facts=True,
        may_present_evidence=True,
    ),
    DialogueIntentDefinition(
        intent_id="reassure",
        category="social",
        description="Lower pressure and reassure the NPC.",
    ),
    DialogueIntentDefinition(
        intent_id="goodbye",
        category="closure",
        description="End the current dialogue scene.",
    ),
)

_INTENT_BY_ID = MappingProxyType({row.intent_id: row for row in _INTENT_CATALOG})


def list_mbam_dialogue_scene_ids() -> tuple[SceneId, ...]:
    return MBAM_DIALOGUE_SCENE_IDS


def list_dialogue_intent_ids() -> tuple[DialogueIntentId, ...]:
    return tuple(row.intent_id for row in _INTENT_CATALOG)


def list_dialogue_intents() -> tuple[DialogueIntentDefinition, ...]:
    return _INTENT_CATALOG


def get_dialogue_intent(intent_id: DialogueIntentId) -> DialogueIntentDefinition:
    return _INTENT_BY_ID[intent_id]


def make_dialogue_scene_state(
    *,
    scene_id: SceneId,
    npc_id: str,
    allowed_intents: tuple[DialogueIntentId, ...] | list[DialogueIntentId],
    required_slots: tuple[DialogueSlotDescriptor, ...] | list[DialogueSlotDescriptor] = (),
    allowed_fact_ids: tuple[str, ...] | list[str] = (),
    revealed_fact_ids: tuple[str, ...] | list[str] = (),
    trust_gate: DialogueTrustGate | None = None,
    stress_gate: DialogueStressGate | None = None,
    repair_paths: tuple[DialogueRepairPath, ...] | list[DialogueRepairPath] = (),
    summary_requirement: DialogueSummaryRequirement | None = None,
    unlock_outputs: DialogueUnlockOutputs | None = None,
    completion_state: SceneCompletionState = "locked",
) -> DialogueSceneState:
    return DialogueSceneState(
        scene_id=scene_id,
        npc_id=npc_id,
        allowed_intents=tuple(allowed_intents),
        required_slots=tuple(required_slots),
        allowed_fact_ids=tuple(allowed_fact_ids),
        revealed_fact_ids=tuple(revealed_fact_ids),
        trust_gate=trust_gate if trust_gate is not None else DialogueTrustGate(),
        stress_gate=stress_gate if stress_gate is not None else DialogueStressGate(),
        repair_paths=tuple(repair_paths),
        summary_requirement=summary_requirement if summary_requirement is not None else DialogueSummaryRequirement(),
        unlock_outputs=unlock_outputs if unlock_outputs is not None else DialogueUnlockOutputs(),
        completion_state=completion_state,
    )


__all__ = [
    "DialogueIntentCategory",
    "DialogueIntentDefinition",
    "DialogueIntentId",
    "DialogueRepairPath",
    "DialogueSceneState",
    "DialogueSlotDescriptor",
    "DialogueSlotName",
    "DialogueStressGate",
    "DialogueStressGateFailureMode",
    "DialogueSummaryRequirement",
    "DialogueTurnRequest",
    "DialogueTurnResult",
    "DialogueTurnSlotValue",
    "DialogueTurnStatus",
    "DialogueTrustGate",
    "DialogueTrustGateFailureMode",
    "DialogueUnlockOutputs",
    "MBAM_DIALOGUE_SCENE_IDS",
    "RepairResponseMode",
    "RepairTrigger",
    "SummaryTargetLanguage",
    "get_dialogue_intent",
    "list_dialogue_intent_ids",
    "list_dialogue_intents",
    "list_mbam_dialogue_scene_ids",
    "make_dialogue_scene_state",
]
