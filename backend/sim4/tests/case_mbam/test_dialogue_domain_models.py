from __future__ import annotations

import pytest

from backend.sim4.case_mbam import (
    DialogueRepairPath,
    DialogueSceneState,
    DialogueSlotDescriptor,
    DialogueStressGate,
    DialogueSummaryRequirement,
    DialogueTurnResult,
    DialogueTrustGate,
    DialogueUnlockOutputs,
    get_dialogue_intent,
    list_dialogue_intent_ids,
    list_mbam_dialogue_scene_ids,
    make_dialogue_scene_state,
)


def test_dialogue_scene_ids_match_locked_s1_to_s5() -> None:
    assert list_mbam_dialogue_scene_ids() == ("S1", "S2", "S3", "S4", "S5")


def test_dialogue_intent_catalog_matches_locked_order() -> None:
    assert list_dialogue_intent_ids() == (
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
    )

    present_evidence = get_dialogue_intent("present_evidence")
    assert present_evidence.required_slot_names == ("item",)
    assert present_evidence.may_present_evidence is True
    assert present_evidence.may_present_facts is True


def test_dialogue_scene_state_structure_is_deterministic_and_validated() -> None:
    scene = make_dialogue_scene_state(
        scene_id="S2",
        npc_id="marc",
        allowed_intents=("request_access", "request_permission", "present_evidence", "summarize_understanding", "goodbye"),
        required_slots=(DialogueSlotDescriptor(slot_name="reason", required=True),),
        allowed_fact_ids=("N2", "N3"),
        revealed_fact_ids=("N2",),
        trust_gate=DialogueTrustGate(minimum_value=0.4, failure_mode="deny"),
        stress_gate=DialogueStressGate(maximum_value=0.9, failure_mode="evade"),
        repair_paths=(DialogueRepairPath(repair_id="S2_REPAIR_MISSING_REASON", trigger="missing_slot", response_mode="sentence_stem"),),
        summary_requirement=DialogueSummaryRequirement(required=True, min_fact_count=1, target_language="fr"),
        unlock_outputs=DialogueUnlockOutputs(
            scene_completion_flags=("scene:S2:completed",),
            new_fact_ids=("N2",),
            new_object_actions=("O6_BADGE_TERMINAL.request_access",),
            new_scene_ids=("S3",),
        ),
        completion_state="available",
    )

    same_scene = make_dialogue_scene_state(
        scene_id="S2",
        npc_id="marc",
        allowed_intents=("request_access", "request_permission", "present_evidence", "summarize_understanding", "goodbye"),
        required_slots=(DialogueSlotDescriptor(slot_name="reason", required=True),),
        allowed_fact_ids=("N2", "N3"),
        revealed_fact_ids=("N2",),
        trust_gate=DialogueTrustGate(minimum_value=0.4, failure_mode="deny"),
        stress_gate=DialogueStressGate(maximum_value=0.9, failure_mode="evade"),
        repair_paths=(DialogueRepairPath(repair_id="S2_REPAIR_MISSING_REASON", trigger="missing_slot", response_mode="sentence_stem"),),
        summary_requirement=DialogueSummaryRequirement(required=True, min_fact_count=1, target_language="fr"),
        unlock_outputs=DialogueUnlockOutputs(
            scene_completion_flags=("scene:S2:completed",),
            new_fact_ids=("N2",),
            new_object_actions=("O6_BADGE_TERMINAL.request_access",),
            new_scene_ids=("S3",),
        ),
        completion_state="available",
    )

    assert scene == same_scene
    assert scene.scene_id == "S2"
    assert scene.npc_id == "marc"
    assert scene.allowed_intents[0] == "request_access"


def test_dialogue_scene_state_rejects_revealed_facts_outside_allowed_slice() -> None:
    with pytest.raises(ValueError, match="subset"):
        DialogueSceneState(
            scene_id="S3",
            npc_id="samira",
            allowed_intents=("ask_when", "ask_where", "goodbye"),
            allowed_fact_ids=("N5",),
            revealed_fact_ids=("N3",),
        )


def test_dialogue_turn_result_requires_repair_mode_for_repair_status() -> None:
    with pytest.raises(ValueError, match="repair_response_mode"):
        DialogueTurnResult(
            scene_id="S1",
            npc_id="elodie",
            intent_id="reassure",
            status="repair",
            code="needs_repair_path",
        )
