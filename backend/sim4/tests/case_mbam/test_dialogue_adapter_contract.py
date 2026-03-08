from __future__ import annotations

import pytest

from backend.sim4.case_mbam import (
    DeterministicDialoguePresentationAdapter,
    DialogueAdapterOutput,
    DialogueTurnRequest,
    build_dialogue_adapter_input,
    build_dialogue_execution_context,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    build_learning_state,
    execute_dialogue_turn,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
    make_dialogue_turn_log_entry,
    validate_dialogue_adapter_output,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def _execute_s1_turn(seed: str = "A"):
    case_state = generate_case_state_for_seed_id(seed)
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    npc_states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    progress = build_initial_investigation_progress(case_state)
    context = build_dialogue_execution_context(progress, npc_states, elapsed_seconds=0.0)
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)

    turn = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="ask_what_happened",
        ),
        context=context,
    )
    assert turn.turn_result.status == "accepted"
    learning_state = build_learning_state(
        case_state=case_state,
        runtime_state=turn.runtime_after,
        progress=progress,
        recent_turns=(make_dialogue_turn_log_entry(turn),),
    )
    return case_state, npc_states, turn, learning_state


def test_build_dialogue_adapter_input_uses_legal_scene_runtime_truth_only() -> None:
    case_state, npc_states, turn, learning_state = _execute_s1_turn("A")
    payload = build_dialogue_adapter_input(
        case_state=case_state,
        turn=turn,
        visible_npc_state=npc_states["elodie"],
        learning_state=learning_state,
    )

    assert payload.scene_id == "S1"
    assert payload.npc_id == "elodie"
    assert payload.intent_id == "ask_what_happened"
    assert payload.turn_status == "accepted"
    assert payload.visible_npc_state is not None
    assert payload.learning_view is not None

    payload_fact_ids = tuple(row.fact_id for row in payload.allowed_fact_payloads)
    assert payload_fact_ids == payload.allowed_fact_ids
    assert set(payload.turn_revealed_fact_ids).issubset(payload.visible_fact_ids)


def test_validate_dialogue_adapter_output_rejects_fact_leakage() -> None:
    case_state, npc_states, turn, learning_state = _execute_s1_turn("A")
    payload = build_dialogue_adapter_input(
        case_state=case_state,
        turn=turn,
        visible_npc_state=npc_states["elodie"],
        learning_state=learning_state,
    )
    leaked_output = DialogueAdapterOutput(
        npc_utterance_text="ligne de test",
        referenced_fact_ids=("N8",),
    )

    with pytest.raises(ValueError, match="outside legal visible slice"):
        validate_dialogue_adapter_output(leaked_output, payload)


def test_deterministic_dialogue_adapter_output_is_stable_for_same_payload() -> None:
    case_state, npc_states, turn, learning_state = _execute_s1_turn("B")
    payload = build_dialogue_adapter_input(
        case_state=case_state,
        turn=turn,
        visible_npc_state=npc_states["elodie"],
        learning_state=learning_state,
    )
    adapter = DeterministicDialoguePresentationAdapter()

    first = adapter.render_turn(payload)
    second = adapter.render_turn(payload)
    assert first == second
    assert first.npc_utterance_text
    assert "mode:" in first.response_mode_metadata[0]

