from __future__ import annotations

from dataclasses import replace

from backend.sim4.case_mbam import (
    DialogueTurnLogEntry,
    build_dialogue_execution_context,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    generate_case_state,
    build_visible_learning_projection,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
)
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


def _setup(seed: str = "A"):
    case_state = generate_case_state_for_seed_id(seed)
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    npc_states = initialize_mbam_npc_states_from_case_state(world_ctx, case_state)
    progress = build_initial_investigation_progress(case_state)
    context = build_dialogue_execution_context(progress, npc_states, elapsed_seconds=0.0)
    runtime = build_initial_dialogue_scene_runtime(case_state, context=context)
    return case_state, progress, runtime


def test_learning_projection_has_difficulty_and_scaffolding_shape() -> None:
    case_state, progress, runtime = _setup("A")
    projection = build_visible_learning_projection(
        case_state=case_state,
        runtime_state=runtime,
        progress=progress,
        recent_turns=(),
    )

    assert projection["difficulty_profile"] in {"D0", "D1"}
    assert projection["current_hint_level"] in {"soft_hint", "sentence_stem"}
    assert projection["scaffolding_policy"]["french_action_required"] is True
    assert projection["scaffolding_policy"]["prompt_generosity"] in {"high", "medium"}
    assert projection["scaffolding_policy"]["confirmation_strength"] in {"explicit", "compact"}
    assert projection["scaffolding_policy"]["summary_strictness"] in {"relaxed", "strict"}
    assert isinstance(projection["summary_by_scene"], list)
    assert isinstance(projection["minigames"], list)


def test_learning_policy_escalates_for_repeated_repair_pressure_on_active_scene() -> None:
    case_state, progress, runtime = _setup("A")
    runtime = replace(runtime, active_scene_id="S2")
    turns = (
        DialogueTurnLogEntry(
            turn_index=1,
            scene_id="S2",
            npc_id="marc",
            intent_id="request_access",
            status="repair",
            code="missing_required_slots",
            outcome="repair",
            response_mode="repair",
            revealed_fact_ids=(),
            trust_delta=0.0,
            stress_delta=0.0,
            missing_required_slots=("reason",),
            repair_response_mode="sentence_stem",
            summary_check_code=None,
        ),
        DialogueTurnLogEntry(
            turn_index=2,
            scene_id="S2",
            npc_id="marc",
            intent_id="request_access",
            status="repair",
            code="wrong_register",
            outcome="repair",
            response_mode="repair",
            revealed_fact_ids=(),
            trust_delta=0.0,
            stress_delta=0.0,
            missing_required_slots=(),
            repair_response_mode="rephrase_choice",
            summary_check_code=None,
        ),
    )

    projection = build_visible_learning_projection(
        case_state=case_state,
        runtime_state=runtime,
        progress=progress,
        recent_turns=turns,
    )

    policy = projection["scaffolding_policy"]
    assert policy["scene_id"] == "S2"
    assert policy["recommended_mode"] in {"sentence_stem", "rephrase_choice", "english_meta_help"}
    assert "soft_hint" in set(policy["allowed_hint_levels"])
    assert policy["reason_code"] == "escalated_after_repairs"


def test_learning_minigame_progress_is_deterministic_from_progress_flags() -> None:
    case_state, progress, runtime = _setup("B")
    progress = replace(
        progress,
        observed_clue_ids=(
            "obs:O3_WALL_LABEL:read",
            "obs:O6_BADGE_TERMINAL:view_logs",
            "obs:O9_RECEIPT_PRINTER:read_receipt",
            "obs:O4_BENCH:inspect",
        ),
        discovered_evidence_ids=("E1_TORN_NOTE",),
        known_fact_ids=("N1", "N3", "N4", "N6"),
    )

    projection = build_visible_learning_projection(
        case_state=case_state,
        runtime_state=runtime,
        progress=progress,
        recent_turns=(),
    )
    rows = {row["minigame_id"]: row for row in projection["minigames"]}

    assert rows["MG1_LABEL_READING"]["completed"] is True
    assert rows["MG2_BADGE_LOG"]["score"] == 2
    assert rows["MG2_BADGE_LOG"]["pass_score_required"] == 2
    assert rows["MG2_BADGE_LOG"]["gate_open"] is True
    assert rows["MG3_RECEIPT_READING"]["completed"] is True
    assert rows["MG4_TORN_NOTE_RECONSTRUCTION"]["completed"] is True
    assert rows["MG4_TORN_NOTE_RECONSTRUCTION"]["max_score"] == 3
    assert rows["MG4_TORN_NOTE_RECONSTRUCTION"]["pass_score_required"] == 3


def test_learning_marks_minigame_retry_when_attempted_but_not_completed() -> None:
    case_state, progress, runtime = _setup("A")
    progress = replace(
        progress,
        observed_clue_ids=("obs:O6_BADGE_TERMINAL:view_logs",),
        known_fact_ids=("N1",),  # N3 missing -> retry-required for MG2
    )
    projection = build_visible_learning_projection(
        case_state=case_state,
        runtime_state=runtime,
        progress=progress,
        recent_turns=(),
    )
    rows = {row["minigame_id"]: row for row in projection["minigames"]}
    assert rows["MG2_BADGE_LOG"]["status"] == "needs_retry"
    assert rows["MG2_BADGE_LOG"]["retry_recommended"] is True


def test_difficulty_profile_changes_scaffolding_and_summary_strictness() -> None:
    case_d0 = generate_case_state(seed="A", difficulty_profile="D0")
    case_d1 = generate_case_state(seed="A", difficulty_profile="D1")
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    npc_d0 = initialize_mbam_npc_states_from_case_state(world_ctx, case_d0)
    npc_d1 = initialize_mbam_npc_states_from_case_state(world_ctx, case_d1)
    progress_d0 = build_initial_investigation_progress(case_d0)
    progress_d1 = build_initial_investigation_progress(case_d1)
    runtime_d0 = build_initial_dialogue_scene_runtime(
        case_d0,
        context=build_dialogue_execution_context(progress_d0, npc_d0, elapsed_seconds=0.0),
    )
    runtime_d1 = build_initial_dialogue_scene_runtime(
        case_d1,
        context=build_dialogue_execution_context(progress_d1, npc_d1, elapsed_seconds=0.0),
    )

    proj_d0 = build_visible_learning_projection(
        case_state=case_d0,
        runtime_state=runtime_d0,
        progress=progress_d0,
        recent_turns=(),
    )
    proj_d1 = build_visible_learning_projection(
        case_state=case_d1,
        runtime_state=runtime_d1,
        progress=progress_d1,
        recent_turns=(),
    )

    assert proj_d0["scaffolding_policy"]["prompt_generosity"] == "high"
    assert proj_d0["scaffolding_policy"]["confirmation_strength"] == "explicit"
    assert proj_d0["scaffolding_policy"]["summary_strictness"] == "relaxed"
    assert proj_d0["scaffolding_policy"]["language_support_level"] == "fr_plus_meta"
    assert proj_d1["scaffolding_policy"]["prompt_generosity"] == "medium"
    assert proj_d1["scaffolding_policy"]["confirmation_strength"] == "compact"
    assert proj_d1["scaffolding_policy"]["summary_strictness"] == "strict"
    assert proj_d1["scaffolding_policy"]["language_support_level"] == "fr_primary"

    summary_d0 = {row["scene_id"]: row for row in proj_d0["summary_by_scene"]}
    summary_d1 = {row["scene_id"]: row for row in proj_d1["summary_by_scene"]}
    assert summary_d0["S5"]["effective_min_fact_count"] == 1
    assert summary_d1["S5"]["effective_min_fact_count"] == 2
    assert summary_d1["S5"]["required_key_fact_ids"] == ["N8"]
