from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
    DialogueTurnRequest,
    DialogueTurnSlotValue,
    apply_dialogue_turn_to_progress,
    build_debug_dialogue_projection,
    build_dialogue_execution_context,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    build_visible_dialogue_projection,
    execute_dialogue_turn,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
    make_dialogue_turn_log_entry,
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


def test_visible_dialogue_projection_has_minimal_safe_shape() -> None:
    case_state, _npc_states, progress, _context, runtime = _setup("A")
    projection = build_visible_dialogue_projection(
        case_state=case_state,
        runtime_state=runtime,
        progress=progress,
        recent_turns=(),
    )

    assert projection["truth_epoch"] == 1
    assert projection["active_scene_id"] is None
    assert len(projection["scene_completion"]) == 5
    assert projection["revealed_fact_ids"] == ["N1"]
    assert projection["recent_turns"] == []
    assert projection["summary_rules"]["required_scene_ids"] == ["S1", "S2", "S3", "S4", "S5"]
    assert projection["learning"]["difficulty_profile"] in {"D0", "D1"}
    assert projection["learning"]["scaffolding_policy"]["french_action_required"] is True
    assert isinstance(projection["learning"]["recent_outcomes"], list)
    s5 = next(row for row in projection["learning"]["summary_by_scene"] if row["scene_id"] == "S5")
    assert "required_key_fact_count" in s5


def test_visible_dialogue_projection_filters_unreached_hidden_fact_ids() -> None:
    case_state, _npc_states, progress, _context, runtime = _setup("A")
    forced_runtime = replace(runtime, revealed_fact_ids=("N1", "N8"))

    projection = build_visible_dialogue_projection(
        case_state=case_state,
        runtime_state=forced_runtime,
        progress=progress,  # N8 not known here
        recent_turns=(),
    )
    assert projection["revealed_fact_ids"] == ["N1"]


def test_dialogue_projection_includes_compact_recent_turn_log() -> None:
    case_state, _npc_states, progress, context, runtime = _setup("A")
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
        context=replace(context, elapsed_seconds=720.0),
    )
    progress_after = apply_dialogue_turn_to_progress(progress, result)
    entry = make_dialogue_turn_log_entry(result)

    visible = build_visible_dialogue_projection(
        case_state=case_state,
        runtime_state=result.runtime_after,
        progress=progress_after,
        recent_turns=(entry,),
    )
    row = visible["recent_turns"][0]
    assert row["scene_id"] == "S4"
    assert row["intent_id"] == "summarize_understanding"
    assert row["status"] == "accepted"
    assert row["code"] == "scene_completed"
    assert row["revealed_fact_ids"] == ["N4", "N5"]
    assert "missing_required_slots" not in row


def test_debug_dialogue_projection_contains_private_runtime_state_for_replay() -> None:
    case_state, _npc_states, progress, context, runtime = _setup("B")
    result = execute_dialogue_turn(
        case_state,
        runtime,
        DialogueTurnRequest(
            scene_id="S2",
            npc_id="marc",
            intent_id="request_access",
            provided_slots=(DialogueTurnSlotValue(slot_name="reason", value="besoin du journal"),),
        ),
        context=replace(
            context,
            elapsed_seconds=120.0,
            npc_states={**context.npc_states, "marc": replace(context.npc_states["marc"], trust=0.9)},
        ),
    )
    entry = make_dialogue_turn_log_entry(result)
    debug = build_debug_dialogue_projection(
        case_state=case_state,
        runtime_state=result.runtime_after,
        progress=progress,
        recent_turns=(entry,),
    )

    assert debug["debug_scope"] == "dialogue_state_private"
    assert debug["runtime_state"]["active_scene_id"] in {"S2", None}
    assert len(debug["recent_turns"]) == 1
    assert "missing_required_slots" in debug["recent_turns"][0]
