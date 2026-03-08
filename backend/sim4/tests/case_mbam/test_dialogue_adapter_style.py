from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
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
    MbamStyleDialoguePresentationAdapter,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def _payload_for_turn(seed: str, request: DialogueTurnRequest, *, elapsed_seconds: float = 0.0, extra_known_facts: tuple[str, ...] = ()):
    case_state = generate_case_state_for_seed_id(seed)
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    npc_states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    progress = build_initial_investigation_progress(case_state)
    if extra_known_facts:
        progress = replace(
            progress,
            known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union(extra_known_facts))),
        )
    context = build_dialogue_execution_context(progress, npc_states, elapsed_seconds=elapsed_seconds)
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)
    turn = execute_dialogue_turn(case_state, runtime, request, context=context)
    learning = build_learning_state(
        case_state=case_state,
        runtime_state=turn.runtime_after,
        progress=progress,
        recent_turns=(make_dialogue_turn_log_entry(turn),),
    )
    return build_dialogue_adapter_input(
        case_state=case_state,
        turn=turn,
        visible_npc_state=npc_states.get(request.npc_id),
        learning_state=learning,
    )


def test_style_adapter_enhances_npc_reply_for_accepted_turn() -> None:
    payload = _payload_for_turn(
        "A",
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id="ask_when"),
    )
    adapter = MbamStyleDialoguePresentationAdapter()
    out = adapter.render_turn(payload)

    assert out.npc_utterance_text
    assert "Élodie Marchand" in out.npc_utterance_text
    assert len(out.npc_utterance_text) <= 180
    assert out.short_rephrase_line is None
    assert out.summary_prompt_line is None


def test_style_adapter_enhances_repair_and_hint_surfaces() -> None:
    payload = _payload_for_turn(
        "A",
        DialogueTurnRequest(scene_id="S3", npc_id="samira", intent_id="ask_when"),
        elapsed_seconds=720.0,
        extra_known_facts=("N2",),
    )
    assert payload.turn_status == "repair"

    adapter = MbamStyleDialoguePresentationAdapter()
    out = adapter.render_turn(payload)

    assert out.npc_utterance_text
    assert out.short_rephrase_line is not None
    assert out.hint_line is not None
    assert "source:style_mbam_v1" in out.response_mode_metadata


def test_style_adapter_adds_summary_prompt_when_summary_required() -> None:
    payload = _payload_for_turn(
        "A",
        DialogueTurnRequest(scene_id="S3", npc_id="samira", intent_id="ask_when"),
        elapsed_seconds=720.0,
        extra_known_facts=("N2",),
    )
    payload = replace(payload, summary_check_code="summary_required")
    adapter = MbamStyleDialoguePresentationAdapter()
    out = adapter.render_turn(payload)
    assert out.summary_prompt_line is not None
    assert "résumé" in out.summary_prompt_line or "resume" in out.summary_prompt_line

