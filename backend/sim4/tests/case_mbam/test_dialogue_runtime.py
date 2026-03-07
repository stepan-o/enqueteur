from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
    DialogueTurnRequest,
    DialogueTurnSlotValue,
    apply_dialogue_turn_to_progress,
    build_dialogue_execution_context,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    enter_dialogue_scene,
    execute_dialogue_turn,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def _setup(seed: str, *, elapsed_seconds: float = 0.0):
    case_state = generate_case_state_for_seed_id(seed)
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    npc_states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    progress = build_initial_investigation_progress(case_state)
    context = build_dialogue_execution_context(
        progress,
        npc_states,
        elapsed_seconds=elapsed_seconds,
    )
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)
    return case_state, npc_states, progress, context, runtime


def _with_npc_trust(context, npc_id: str, trust: float):
    states = dict(context.npc_states)
    states[npc_id] = replace(states[npc_id], trust=trust)
    return replace(context, npc_states=states)


def test_initial_dialogue_runtime_exposes_seed_deterministic_scene_states() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")
    same_runtime = build_initial_dialogue_scene_runtime(case_state, context=context)

    assert runtime == same_runtime
    assert runtime.scene_completion_states == (
        ("S1", "available"),
        ("S2", "available"),
        ("S3", "locked"),
        ("S4", "available"),
        ("S5", "locked"),
    )
    assert runtime.surfaced_scene_ids == ("S1", "S2", "S4")


def test_enter_scene_enforces_gate_prereqs_and_npc_binding() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")

    blocked = enter_dialogue_scene(
        case_state,
        runtime,
        scene_id="S3",
        npc_id="samira",
        context=context,
    )
    assert blocked.status == "blocked_gate"
    assert blocked.code == "missing_required_facts"
    assert blocked.gate_check.missing_fact_ids == ("N2",)

    entered = enter_dialogue_scene(
        case_state,
        runtime,
        scene_id="S1",
        npc_id="elodie",
        context=context,
    )
    assert entered.status == "entered"
    assert entered.scene_state_after.completion_state == "in_progress"
    assert entered.runtime_after.active_scene_id == "S1"
    assert entered.revealed_fact_ids == ("N1",)


def test_turn_rejects_invalid_intent_and_repairs_missing_slots() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")
    trust_context = _with_npc_trust(context, "marc", 0.8)

    invalid_intent = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="request_access"),
        context=context,
    )
    assert invalid_intent.turn_result.status == "invalid_intent"
    assert invalid_intent.turn_result.code == "intent_not_allowed_for_scene"
    assert invalid_intent.outcome == "rejected"

    missing_reason = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(scene_id="S2", npc_id="marc", intent_id="request_access"),
        context=trust_context,
    )
    assert missing_reason.turn_result.status == "repair"
    assert missing_reason.turn_result.code == "missing_required_slots"
    assert missing_reason.turn_result.missing_required_slots == ("reason",)
    assert missing_reason.outcome == "repair"


def test_turn_blocks_when_scene_time_window_or_trust_gate_fails() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A", elapsed_seconds=1000.0)

    time_blocked = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S2",
            npc_id="marc",
            intent_id="request_access",
            provided_slots=(DialogueTurnSlotValue(slot_name="reason", value="vérifier le terminal"),),
        ),
        context=_with_npc_trust(context, "marc", 0.9),
    )
    assert time_blocked.turn_result.status == "blocked_gate"
    assert time_blocked.turn_result.code == "outside_time_window"
    assert "outside_time_window" in time_blocked.gate_check.failure_reasons

    trust_blocked = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S2",
            npc_id="marc",
            intent_id="request_access",
            provided_slots=(DialogueTurnSlotValue(slot_name="reason", value="vérifier le terminal"),),
        ),
        context=_with_npc_trust(replace(context, elapsed_seconds=120.0), "marc", 0.05),
    )
    assert trust_blocked.turn_result.status == "refused"
    assert trust_blocked.turn_result.code == "insufficient_trust"


def test_summary_turn_completes_scene_and_emits_unlock_outputs() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")

    result = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="summarize_understanding",
            presented_fact_ids=("N1",),
        ),
        context=context,
    )
    assert result.turn_result.status == "accepted"
    assert result.turn_result.code == "scene_completed"
    assert result.turn_result.summary_check_passed is True
    assert result.turn_result.revealed_fact_ids == ("N1",)
    assert result.summary_check is not None
    assert result.summary_check.passed is True
    assert result.scene_state_after.completion_state == "completed"
    assert result.runtime_after.active_scene_id is None
    assert "scene:S1:inspection_permission" in result.runtime_after.emitted_scene_completion_flags
    assert "O1_DISPLAY_CASE.inspect" in result.runtime_after.emitted_object_action_unlocks


def test_summary_insufficient_facts_repairs_and_does_not_complete_scene() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")
    context_for_s5 = _with_npc_trust(
        replace(
            context,
            known_fact_ids=("N1", "N3", "N4", "N8"),
            collected_evidence_ids=("E2_CAFE_RECEIPT",),
        ),
        "elodie",
        0.9,
    )

    result = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S5",
            npc_id="elodie",
            intent_id="summarize_understanding",
            presented_fact_ids=("N1",),  # not in S5 allowed set and below min_fact_count=2
        ),
        context=context_for_s5,
    )
    assert result.turn_result.status == "repair"
    assert result.turn_result.code == "summary_insufficient_facts"
    assert result.summary_check is not None
    assert result.summary_check.passed is False
    assert result.scene_state_after.completion_state == "in_progress"


def test_dialogue_turn_can_project_revealed_facts_into_investigation_progress() -> None:
    case_state, _npc_states, progress, context, runtime = _setup("A", elapsed_seconds=720.0)

    result = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S4",
            npc_id="jo",
            intent_id="summarize_understanding",
            provided_slots=(DialogueTurnSlotValue(slot_name="time", value="17h52"),),
            presented_fact_ids=("N1",),
        ),
        context=context,
    )
    after = apply_dialogue_turn_to_progress(progress, result)
    assert "N4" in after.known_fact_ids
    assert "N5" in after.known_fact_ids


def test_present_evidence_requires_known_evidence_reference() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")
    trust_context = _with_npc_trust(context, "marc", 0.8)

    missing = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S2",
            npc_id="marc",
            intent_id="present_evidence",
            provided_slots=(
                DialogueTurnSlotValue(slot_name="reason", value="regarder ce ticket"),
                DialogueTurnSlotValue(slot_name="item", value="reçu du café"),
            ),
        ),
        context=trust_context,
    )
    assert missing.turn_result.status == "repair"
    assert missing.turn_result.code == "missing_evidence_reference"

    unknown = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S2",
            npc_id="marc",
            intent_id="present_evidence",
            provided_slots=(
                DialogueTurnSlotValue(slot_name="reason", value="regarder ce ticket"),
                DialogueTurnSlotValue(slot_name="item", value="reçu du café"),
            ),
            presented_evidence_ids=("E2_CAFE_RECEIPT",),
        ),
        context=trust_context,
    )
    assert unknown.turn_result.status == "refused"
    assert unknown.turn_result.code == "presented_evidence_not_known"


def test_wrong_register_and_high_stress_produce_deterministic_non_accept_paths() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")

    wrong_register = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="ask_what_happened",
            utterance_text="REGISTER:WRONG informal",
        ),
        context=context,
    )
    assert wrong_register.turn_result.status == "repair"
    assert wrong_register.turn_result.code == "wrong_register"
    assert wrong_register.response_mode == "repair"

    stressed_context = replace(
        context,
        npc_states={
            **context.npc_states,
            "elodie": replace(context.npc_states["elodie"], stress=0.95, trust=0.8),
        },
    )
    stress_refusal = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_what_happened"),
        context=stressed_context,
    )
    assert stress_refusal.turn_result.status == "refused"
    assert stress_refusal.turn_result.code.startswith("excessive_stress_")


def test_legal_fact_reveal_is_scene_bound_and_stateful() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")

    first = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="request_permission"),
        context=context,
    )
    assert "N7" in first.turn_result.revealed_fact_ids
    assert "N7" in first.runtime_after.revealed_fact_ids

    second = execute_dialogue_turn(
        case_state,
        first.runtime_after,
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="request_permission"),
        context=context,
    )
    # Already-known legal fact should not be duplicated as newly revealed.
    assert second.turn_result.revealed_fact_ids == ()


def test_dialogue_turn_execution_is_deterministic_for_same_inputs() -> None:
    case_state, _npc_states, _progress, context, runtime = _setup("A")
    request = DialogueTurnRequest(
        scene_id="S1",
        npc_id="elodie",
        intent_id="summarize_understanding",
        presented_fact_ids=("N1",),
    )
    first = execute_dialogue_turn(case_state, runtime, request, context=context)
    second = execute_dialogue_turn(case_state, runtime, request, context=context)
    assert first == second
