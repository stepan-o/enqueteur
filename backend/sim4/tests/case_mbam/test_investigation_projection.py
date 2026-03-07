from __future__ import annotations

from backend.sim4.case_mbam import (
    apply_execution_result_to_progress,
    build_debug_investigation_projection,
    build_initial_investigation_progress,
    build_initial_mbam_object_state,
    build_visible_investigation_projection,
    execute_investigation_command,
    generate_case_state_for_seed_id,
    make_investigation_command,
)


def test_visible_investigation_projection_has_minimal_safe_shape() -> None:
    case_state = generate_case_state_for_seed_id("B")
    object_state = build_initial_mbam_object_state(case_state)
    progress = build_initial_investigation_progress(case_state)

    projection = build_visible_investigation_projection(
        case_state=case_state,
        object_state=object_state,
        progress=progress,
    )
    assert projection["truth_epoch"] == 1
    assert len(projection["objects"]) == 10
    assert projection["facts"]["known_fact_ids"] == ["N1"]
    assert projection["evidence"]["discovered_ids"] == []
    assert projection["contradictions"]["unlockable_edge_ids"] == []

    medallion = next(row for row in projection["objects"] if row["object_id"] == "O2_MEDALLION")
    assert medallion["known_state"] == {}


def test_visible_projection_tracks_discovered_evidence_without_hidden_truth_leak() -> None:
    case_state = generate_case_state_for_seed_id("C")
    object_state = build_initial_mbam_object_state(case_state)
    progress = build_initial_investigation_progress(case_state)

    execution = execute_investigation_command(
        make_investigation_command(
            object_id="O1_DISPLAY_CASE",
            affordance_id="examine_surface",
        ),
        case_state=case_state,
        object_state=object_state,
    )
    updated = apply_execution_result_to_progress(case_state, progress, execution).progress_after

    projection = build_visible_investigation_projection(
        case_state=case_state,
        object_state=execution.object_state_after,
        progress=updated,
    )

    assert projection["evidence"]["discovered_ids"] == ["E3_METHOD_TRACE"]
    assert projection["evidence"]["collected_ids"] == []
    assert "clue:evidence:E3_METHOD_TRACE:observed_not_collected" in projection["evidence"]["observed_not_collected_ids"]

    medallion = next(row for row in projection["objects"] if row["object_id"] == "O2_MEDALLION")
    assert "location" not in medallion["known_state"]
    assert "drop_coat_rack_pocket" not in str(projection)


def test_debug_investigation_projection_includes_full_state_for_replay_debug() -> None:
    case_state = generate_case_state_for_seed_id("A")
    object_state = build_initial_mbam_object_state(case_state)
    progress = build_initial_investigation_progress(case_state)

    projection = build_debug_investigation_projection(
        case_state=case_state,
        object_state=object_state,
        progress=progress,
    )

    assert projection["debug_scope"] == "investigation_state_private"
    assert projection["seed"] == "A"
    assert projection["object_state"]["o2_medallion"]["location"] == "corridor_bin"
    assert projection["object_state"]["o6_badge_terminal"]["archived"] is False
    assert projection["progress"]["known_fact_ids"] == ["N1"]
    assert projection["progress"]["consumed_action_keys"] == []


def test_visible_projection_updates_known_object_state_after_observation() -> None:
    case_state = generate_case_state_for_seed_id("A")
    object_state = build_initial_mbam_object_state(case_state)
    progress = build_initial_investigation_progress(case_state)

    execution = execute_investigation_command(
        make_investigation_command(
            object_id="O8_KEYPAD_DOOR",
            affordance_id="inspect",
        ),
        case_state=case_state,
        object_state=object_state,
    )
    updated = apply_execution_result_to_progress(case_state, progress, execution).progress_after
    projection = build_visible_investigation_projection(
        case_state=case_state,
        object_state=execution.object_state_after,
        progress=updated,
    )
    keypad = next(row for row in projection["objects"] if row["object_id"] == "O8_KEYPAD_DOOR")
    assert keypad["observed_affordances"] == ["inspect"]
    assert keypad["known_state"]["locked"] is True
    assert keypad["known_state"]["has_code_hint"] is True
