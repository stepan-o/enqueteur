from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
    DialogueTurnRequest,
    build_dialogue_adapter_input,
    build_dialogue_adapter_prompt_context,
    build_dialogue_execution_context,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    build_learning_state,
    build_safe_dialogue_adapter_context,
    build_safe_dialogue_adapter_context_from_turn,
    execute_dialogue_turn,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
    make_dialogue_turn_log_entry,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def _setup(seed: str = "A"):
    case_state = generate_case_state_for_seed_id(seed)
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    npc_states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    progress = build_initial_investigation_progress(case_state)
    return case_state, npc_states, progress


def test_safe_packaging_excludes_unrevealed_allowed_fact_content() -> None:
    case_state, npc_states, progress = _setup("A")
    context = build_dialogue_execution_context(progress, npc_states, elapsed_seconds=0.0)
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)

    turn = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_what_happened"),
        context=context,
    )
    assert turn.turn_result.status == "accepted"

    learning_state = build_learning_state(
        case_state=case_state,
        runtime_state=turn.runtime_after,
        progress=progress,
        recent_turns=(make_dialogue_turn_log_entry(turn),),
    )
    payload = build_dialogue_adapter_input(
        case_state=case_state,
        turn=turn,
        visible_npc_state=npc_states["elodie"],
        learning_state=learning_state,
    )
    assert "N7" in payload.allowed_fact_ids

    package = build_safe_dialogue_adapter_context(payload)
    assert package.scene_id == "S1"
    assert package.npc_identity.display_name == "Élodie Marchand"
    assert package.npc_identity.identity_role == "curator"
    assert package.visible_npc_state is not None

    # S1 allows N1/N7, but only revealed-visible facts are package-legal.
    assert package.legal_facts.visible_fact_ids == ("N1",)
    assert package.legal_facts.newly_revealed_fact_ids == ()
    assert tuple(row.fact_id for row in package.legal_facts.visible_fact_payloads) == ("N1",)


def test_safe_packaging_includes_repair_turn_classification_without_hidden_truth() -> None:
    case_state, npc_states, progress = _setup("A")
    progress = replace(
        progress,
        known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union({"N2"}))),
    )
    context = build_dialogue_execution_context(progress, npc_states, elapsed_seconds=0.0)
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)

    turn = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(scene_id="S3", npc_id="samira", intent_id="ask_when"),
        context=context,
    )
    assert turn.turn_result.status == "repair"
    assert turn.turn_result.repair_response_mode is not None

    package = build_safe_dialogue_adapter_context_from_turn(
        case_state=case_state,
        turn=turn,
        visible_npc_state=npc_states["samira"],
        learning_state=None,
    )
    assert package.turn.turn_status == "repair"
    assert package.turn.repair_response_mode is not None
    assert package.turn.turn_code == "missing_required_slots"

    prompt = build_dialogue_adapter_prompt_context(package)
    joined = "\n".join((*prompt.guardrails, *prompt.legal_fact_lines))
    assert "do_not_invent_facts" in prompt.guardrails
    assert "do_not_predict_future_outcomes" in prompt.guardrails
    assert "N8:" not in joined


def test_safe_packaging_and_prompt_context_are_deterministic_for_same_turn() -> None:
    case_state, npc_states, progress = _setup("B")
    context = build_dialogue_execution_context(progress, npc_states, elapsed_seconds=0.0)
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)

    turn = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_where"),
        context=context,
    )
    learning_state = build_learning_state(
        case_state=case_state,
        runtime_state=turn.runtime_after,
        progress=progress,
        recent_turns=(make_dialogue_turn_log_entry(turn),),
    )
    first = build_safe_dialogue_adapter_context_from_turn(
        case_state=case_state,
        turn=turn,
        visible_npc_state=npc_states["elodie"],
        learning_state=learning_state,
    )
    second = build_safe_dialogue_adapter_context_from_turn(
        case_state=case_state,
        turn=turn,
        visible_npc_state=npc_states["elodie"],
        learning_state=learning_state,
    )
    assert first == second
    assert build_dialogue_adapter_prompt_context(first) == build_dialogue_adapter_prompt_context(second)

