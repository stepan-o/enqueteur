from __future__ import annotations

"""Deterministic MBAM structured scene definitions (Phase 4B).

This module provides canonical, data-driven scene definitions for S1..S5 and
keeps them explicitly aligned with CaseState scene gates.
"""

from dataclasses import dataclass
from typing import cast

from .dialogue_domain import (
    DialogueRepairPath,
    DialogueSceneState,
    DialogueSlotDescriptor,
    DialogueStressGate,
    DialogueSummaryRequirement,
    DialogueTrustGate,
    DialogueUnlockOutputs,
    make_dialogue_scene_state,
)
from .models import CaseState, SceneCompletionState, SceneGate, SceneId


@dataclass(frozen=True)
class DialogueSceneProgressionModel:
    initial_state: SceneCompletionState
    success_state: SceneCompletionState = "completed"
    soft_failure_state: SceneCompletionState = "failed_soft"


@dataclass(frozen=True)
class MbamSceneDefinition:
    scene_id: SceneId
    primary_npc_id: str
    goal_summary: str
    case_gate: SceneGate
    scene_state: DialogueSceneState
    progression: DialogueSceneProgressionModel

    def __post_init__(self) -> None:
        if self.scene_state.scene_id != self.scene_id:
            raise ValueError("MbamSceneDefinition.scene_state.scene_id must match scene_id")
        if not self.primary_npc_id:
            raise ValueError("MbamSceneDefinition.primary_npc_id must be non-empty")
        allowed_fact_set = set(self.scene_state.allowed_fact_ids)
        for required_fact in self.case_gate.required_fact_ids:
            if required_fact not in allowed_fact_set:
                raise ValueError(
                    f"Scene {self.scene_id} case gate fact {required_fact!r} "
                    "must be included in scene_state.allowed_fact_ids"
                )


@dataclass(frozen=True)
class MbamSceneDefinitions:
    S1: MbamSceneDefinition
    S2: MbamSceneDefinition
    S3: MbamSceneDefinition
    S4: MbamSceneDefinition
    S5: MbamSceneDefinition


def _scene_gate_for_id(case_state: CaseState, scene_id: SceneId) -> SceneGate:
    return cast(SceneGate, getattr(case_state.scene_gates, scene_id))


def _initial_completion_state(case_state: CaseState, scene_id: SceneId) -> SceneCompletionState:
    gate = _scene_gate_for_id(case_state, scene_id)
    known_facts = set(case_state.visible_case_slice.starting_known_fact_ids)
    has_required_facts = all(fact_id in known_facts for fact_id in gate.required_fact_ids)
    # Starting inventory is intentionally empty in this phase.
    has_required_items = len(gate.required_items) == 0
    if has_required_facts and has_required_items:
        return "available"
    return "locked"


def _summary_requirement(scene_id: SceneId) -> DialogueSummaryRequirement:
    if scene_id == "S5":
        return DialogueSummaryRequirement(required=True, min_fact_count=2, target_language="fr")
    return DialogueSummaryRequirement(required=True, min_fact_count=1, target_language="fr")


def _scene_s3_primary_npc(case_state: CaseState) -> str:
    # Spec allows "Samira or equivalent". Lock deterministic fallback:
    # when Samira is culprit, route timeline witnessing through Elodie.
    if case_state.roles_assignment.culprit == "samira":
        return "elodie"
    return "samira"


def _make_scene_definition(case_state: CaseState, scene_id: SceneId) -> MbamSceneDefinition:
    gate = _scene_gate_for_id(case_state, scene_id)
    initial_state = _initial_completion_state(case_state, scene_id)

    if scene_id == "S1":
        primary_npc_id = "elodie"
        goal_summary = "Establish incident context and grant inspection permission."
        scene_state = make_dialogue_scene_state(
            scene_id="S1",
            npc_id=primary_npc_id,
            allowed_intents=(
                "ask_what_happened",
                "ask_when",
                "ask_where",
                "ask_who",
                "request_permission",
                "summarize_understanding",
                "reassure",
                "goodbye",
            ),
            required_slots=(),
            allowed_fact_ids=("N1", "N7"),
            revealed_fact_ids=("N1",),
            trust_gate=DialogueTrustGate(minimum_value=gate.trust_threshold, failure_mode="deflect"),
            stress_gate=DialogueStressGate(maximum_value=0.90, failure_mode="switch_register"),
            repair_paths=(
                DialogueRepairPath(
                    repair_id="S1_REPAIR_WRONG_REGISTER",
                    trigger="wrong_register",
                    response_mode="sentence_stem",
                ),
                DialogueRepairPath(
                    repair_id="S1_REPAIR_AGGRESSIVE",
                    trigger="too_aggressive",
                    response_mode="meta_hint",
                ),
            ),
            summary_requirement=_summary_requirement("S1"),
            unlock_outputs=DialogueUnlockOutputs(
                scene_completion_flags=("scene:S1:intro_established", "scene:S1:inspection_permission"),
                new_fact_ids=("N1",),
                new_object_actions=("O1_DISPLAY_CASE.inspect", "O1_DISPLAY_CASE.check_lock"),
                new_scene_ids=("S2", "S4"),
            ),
            completion_state=initial_state,
        )
    elif scene_id == "S2":
        primary_npc_id = "marc"
        goal_summary = "Gain badge-log access path or procedural security clue."
        scene_state = make_dialogue_scene_state(
            scene_id="S2",
            npc_id=primary_npc_id,
            allowed_intents=(
                "ask_what_seen",
                "ask_when",
                "request_access",
                "request_permission",
                "present_evidence",
                "summarize_understanding",
                "reassure",
                "goodbye",
            ),
            required_slots=(DialogueSlotDescriptor(slot_name="reason", required=True),),
            allowed_fact_ids=("N1", "N2", "N3", "N7"),
            revealed_fact_ids=(),
            trust_gate=DialogueTrustGate(minimum_value=gate.trust_threshold, failure_mode="delay"),
            stress_gate=DialogueStressGate(maximum_value=0.85, failure_mode="evade"),
            repair_paths=(
                DialogueRepairPath(
                    repair_id="S2_REPAIR_MISSING_REASON",
                    trigger="missing_slot",
                    response_mode="sentence_stem",
                ),
                DialogueRepairPath(
                    repair_id="S2_REPAIR_WEAK_EVIDENCE",
                    trigger="weak_evidence",
                    response_mode="alternate_path",
                ),
                DialogueRepairPath(
                    repair_id="S2_REPAIR_BYPASS_PROCESS",
                    trigger="too_aggressive",
                    response_mode="rephrase_choice",
                ),
            ),
            summary_requirement=_summary_requirement("S2"),
            unlock_outputs=DialogueUnlockOutputs(
                scene_completion_flags=("scene:S2:security_gate_progress",),
                new_fact_ids=("N2",),
                new_object_actions=("O6_BADGE_TERMINAL.request_access", "O6_BADGE_TERMINAL.view_logs"),
                new_scene_ids=("S3",),
            ),
            completion_state=initial_state,
        )
    elif scene_id == "S3":
        primary_npc_id = _scene_s3_primary_npc(case_state)
        goal_summary = "Build the timeline sequence with room/time witness detail."
        scene_state = make_dialogue_scene_state(
            scene_id="S3",
            npc_id=primary_npc_id,
            allowed_intents=(
                "ask_when",
                "ask_where",
                "ask_who",
                "ask_what_seen",
                "present_evidence",
                "challenge_contradiction",
                "summarize_understanding",
                "reassure",
                "goodbye",
            ),
            required_slots=(DialogueSlotDescriptor(slot_name="time", required=True),),
            allowed_fact_ids=("N2", "N3", "N5", "N6", "N7", "N8"),
            revealed_fact_ids=(),
            trust_gate=DialogueTrustGate(minimum_value=gate.trust_threshold, failure_mode="deflect"),
            stress_gate=DialogueStressGate(maximum_value=0.88, failure_mode="evade"),
            repair_paths=(
                DialogueRepairPath(
                    repair_id="S3_REPAIR_MISSING_TIME",
                    trigger="missing_slot",
                    response_mode="sentence_stem",
                ),
                DialogueRepairPath(
                    repair_id="S3_REPAIR_PRESSURE",
                    trigger="too_aggressive",
                    response_mode="meta_hint",
                ),
            ),
            summary_requirement=_summary_requirement("S3"),
            unlock_outputs=DialogueUnlockOutputs(
                scene_completion_flags=("scene:S3:timeline_sequence_built",),
                new_fact_ids=("N3", "N6"),
                new_object_actions=("O7_SECURITY_BINDER.read",),
                new_scene_ids=("S4", "S5"),
            ),
            completion_state=initial_state,
        )
    elif scene_id == "S4":
        primary_npc_id = "jo"
        goal_summary = "Get café witness clothing and timestamp clues."
        scene_state = make_dialogue_scene_state(
            scene_id="S4",
            npc_id=primary_npc_id,
            allowed_intents=(
                "ask_what_seen",
                "ask_when",
                "ask_where",
                "ask_who",
                "present_evidence",
                "summarize_understanding",
                "reassure",
                "goodbye",
            ),
            required_slots=(DialogueSlotDescriptor(slot_name="time", required=True),),
            allowed_fact_ids=("N1", "N4", "N5"),
            revealed_fact_ids=(),
            trust_gate=DialogueTrustGate(minimum_value=gate.trust_threshold, failure_mode="deflect"),
            stress_gate=DialogueStressGate(maximum_value=0.95, failure_mode="switch_register"),
            repair_paths=(
                DialogueRepairPath(
                    repair_id="S4_REPAIR_MISSING_TIME",
                    trigger="missing_slot",
                    response_mode="rephrase_choice",
                ),
                DialogueRepairPath(
                    repair_id="S4_REPAIR_STIFF_TONE",
                    trigger="wrong_register",
                    response_mode="meta_hint",
                ),
            ),
            summary_requirement=_summary_requirement("S4"),
            unlock_outputs=DialogueUnlockOutputs(
                scene_completion_flags=("scene:S4:cafe_witness_obtained",),
                new_fact_ids=("N4", "N5"),
                new_object_actions=("O9_RECEIPT_PRINTER.ask_for_receipt", "O9_RECEIPT_PRINTER.read_receipt"),
                new_scene_ids=("S5",),
            ),
            completion_state=initial_state,
        )
    elif scene_id == "S5":
        primary_npc_id = "elodie"
        goal_summary = "Confront and resolve via recovery path or accusation path."
        scene_state = make_dialogue_scene_state(
            scene_id="S5",
            npc_id=primary_npc_id,
            allowed_intents=(
                "present_evidence",
                "challenge_contradiction",
                "summarize_understanding",
                "accuse",
                "request_permission",
                "reassure",
                "goodbye",
            ),
            required_slots=(
                DialogueSlotDescriptor(slot_name="person", required=True),
                DialogueSlotDescriptor(slot_name="reason", required=True),
            ),
            allowed_fact_ids=("N3", "N4", "N5", "N6", "N7", "N8"),
            revealed_fact_ids=(),
            trust_gate=DialogueTrustGate(minimum_value=gate.trust_threshold, failure_mode="deny"),
            stress_gate=DialogueStressGate(maximum_value=0.82, failure_mode="shut_down"),
            repair_paths=(
                DialogueRepairPath(
                    repair_id="S5_REPAIR_WEAK_EVIDENCE",
                    trigger="weak_evidence",
                    response_mode="alternate_path",
                ),
                DialogueRepairPath(
                    repair_id="S5_REPAIR_MISSING_REASON",
                    trigger="missing_slot",
                    response_mode="sentence_stem",
                ),
                DialogueRepairPath(
                    repair_id="S5_REPAIR_AGGRESSIVE",
                    trigger="too_aggressive",
                    response_mode="meta_hint",
                ),
            ),
            summary_requirement=_summary_requirement("S5"),
            unlock_outputs=DialogueUnlockOutputs(
                scene_completion_flags=("scene:S5:confrontation_resolution",),
                new_fact_ids=("N8",),
                new_object_actions=(),
                new_scene_ids=(),
            ),
            completion_state=initial_state,
        )
    else:
        raise ValueError(f"Unsupported scene_id: {scene_id!r}")

    return MbamSceneDefinition(
        scene_id=scene_id,
        primary_npc_id=primary_npc_id,
        goal_summary=goal_summary,
        case_gate=gate,
        scene_state=scene_state,
        progression=DialogueSceneProgressionModel(initial_state=initial_state),
    )


def build_mbam_scene_definitions(case_state: CaseState) -> MbamSceneDefinitions:
    return MbamSceneDefinitions(
        S1=_make_scene_definition(case_state, "S1"),
        S2=_make_scene_definition(case_state, "S2"),
        S3=_make_scene_definition(case_state, "S3"),
        S4=_make_scene_definition(case_state, "S4"),
        S5=_make_scene_definition(case_state, "S5"),
    )


def get_mbam_scene_definition(scene_definitions: MbamSceneDefinitions, scene_id: SceneId) -> MbamSceneDefinition:
    return cast(MbamSceneDefinition, getattr(scene_definitions, scene_id))


def list_mbam_scene_definitions(scene_definitions: MbamSceneDefinitions) -> tuple[MbamSceneDefinition, ...]:
    return (
        scene_definitions.S1,
        scene_definitions.S2,
        scene_definitions.S3,
        scene_definitions.S4,
        scene_definitions.S5,
    )


__all__ = [
    "DialogueSceneProgressionModel",
    "MbamSceneDefinition",
    "MbamSceneDefinitions",
    "build_mbam_scene_definitions",
    "get_mbam_scene_definition",
    "list_mbam_scene_definitions",
]
