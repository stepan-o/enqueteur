from __future__ import annotations

import json
from pathlib import Path

from backend.sim4.ecs.world import ECSWorld
from backend.sim4.host.kvp_defaults import (
    default_render_spec,
    default_run_anchors,
    tick_rate_hz_from_clock,
)
from backend.sim4.case_mbam import DialogueTurnRequest
from backend.sim4.host.sim_runner import MbamCaseConfig, OfflineExportConfig, SimRunner
from backend.sim4.integration.manifest_schema import ManifestV0_1
from backend.sim4.integration.record_writer import read_record
from backend.sim4.runtime.clock import TickClock
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


class _NoopScheduler:
    def iter_phase_systems(self, phase: str):  # noqa: ARG002
        return ()


def _export_single_tick_state(
    tmp_path: Path,
    *,
    channels: list[str],
    case_seed: str = "B",
) -> tuple[dict, SimRunner]:
    clock = TickClock(dt=1.0 / 30.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    run_root = tmp_path / f"run_{case_seed}_{'_'.join(channels)}"
    offline = OfflineExportConfig(
        run_root=run_root,
        channels=channels,
        keyframe_ticks=[1],
        validate=False,
    )

    runner = SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(seed=123, tick_rate_hz=tick_rate_hz_from_clock(clock), time_origin_ms=0),
        render_spec=default_render_spec(),
        channels=channels,
        offline=offline,
        case_config=MbamCaseConfig(seed=case_seed),
    )
    runner.run(num_ticks=1)

    manifest = ManifestV0_1.from_dict(json.loads((run_root / "manifest.kvp.json").read_text("utf-8")))
    snap_ptr = manifest.snapshots[manifest.available_start_tick]
    env = read_record(run_root / snap_ptr.rel_path)
    return env["payload"]["state"], runner


def test_runner_exports_visible_case_projection_for_single_tick(tmp_path: Path):
    state, runner = _export_single_tick_state(tmp_path, channels=["WORLD", "DEBUG"], case_seed="B")

    case_state = runner.get_case_state()
    assert case_state is not None
    assert case_state.case_id == "MBAM_01"
    assert case_state.seed == "B"

    assert "case" in state
    assert state["case"]["case_id"] == "MBAM_01"
    assert state["case"]["seed"] == "B"
    assert state["case"]["truth_epoch"] == 1
    assert state["case"]["visible_case_slice"]["starting_scene_id"] == "S1"
    assert "N1" in state["case"]["visible_case_slice"]["starting_known_fact_ids"]
    assert "roles_assignment" not in state["case"]
    assert "hidden_case_slice" not in state["case"]

    assert "npc_semantic" in state
    assert len(state["npc_semantic"]) == 5
    samira_public = next(row for row in state["npc_semantic"] if row["npc_id"] == "samira")
    assert "overlay_role_slot" not in samira_public
    assert "known_fact_flags" not in samira_public
    assert "profile_id" not in samira_public["card_state"]
    assert "investigation" in state
    assert "objects" in state["investigation"]
    assert "evidence" in state["investigation"]
    assert "facts" in state["investigation"]
    assert "contradictions" in state["investigation"]
    assert len(state["investigation"]["objects"]) == 10
    assert "dialogue" in state
    assert state["dialogue"]["active_scene_id"] is None
    assert len(state["dialogue"]["scene_completion"]) == 5
    assert state["dialogue"]["revealed_fact_ids"] == ["N1"]
    assert state["dialogue"]["recent_turns"] == []
    assert "learning" in state
    assert state["learning"]["difficulty_profile"] in {"D0", "D1"}
    assert state["learning"]["current_hint_level"] in {"soft_hint", "sentence_stem", "rephrase_choice", "english_meta_help"}
    assert "minigames" in state["learning"]
    assert "summary_by_scene" in state["learning"]
    assert "recent_outcomes" in state["learning"]
    assert state["learning"] == state["dialogue"]["learning"]
    assert "case_outcome" in state
    assert state["case_outcome"]["primary_outcome"] in {
        "in_progress",
        "recovery_success",
        "accusation_success",
        "soft_fail",
        "best_outcome",
    }
    assert state["case_outcome"]["soft_fail_latched"] is False
    assert state["case_outcome"]["best_outcome_awarded"] is False
    assert state["case_outcome"]["soft_fail_reasons"] == []
    assert state["case_outcome"]["continuity_flags"] == []
    assert "action_flags" not in state["case_outcome"]
    assert "case_recap" in state
    assert state["case_recap"]["final_outcome_type"] == state["case_outcome"]["primary_outcome"]
    assert state["case_recap"]["resolution_path"] in {"in_progress", "recovery", "accusation", "soft_fail"}
    assert isinstance(state["case_recap"]["key_fact_ids"], list)
    assert isinstance(state["case_recap"]["key_evidence_ids"], list)
    assert isinstance(state["case_recap"]["continuity_flags"], list)

    assert "debug" in state
    assert "case_private" in state["debug"]
    assert state["debug"]["case_private"]["roles_assignment"]["culprit"] == "samira"
    assert "npc_semantic_private" in state["debug"]
    samira_private = next(row for row in state["debug"]["npc_semantic_private"] if row["npc_id"] == "samira")
    assert samira_private["overlay_role_slot"] == "CULPRIT"
    assert "investigation_private" in state["debug"]
    assert "object_state" in state["debug"]["investigation_private"]
    assert "progress" in state["debug"]["investigation_private"]
    assert "dialogue_private" in state["debug"]
    assert "runtime_state" in state["debug"]["dialogue_private"]
    assert "recent_turns" in state["debug"]["dialogue_private"]
    assert "learning_private" in state["debug"]
    assert state["debug"]["learning_private"]["difficulty_profile"] in {"D0", "D1"}
    assert "recent_outcomes" in state["debug"]["learning_private"]
    assert "case_outcome_private" in state["debug"]
    assert state["debug"]["case_outcome_private"]["debug_scope"] == "outcome_state_private"
    assert "case_recap_private" in state["debug"]
    assert state["debug"]["case_recap_private"]["debug_scope"] == "run_recap_private"


def test_runner_omits_private_case_projection_without_debug_channel(tmp_path: Path):
    state, _runner = _export_single_tick_state(tmp_path, channels=["WORLD"], case_seed="C")

    assert "case" in state
    assert state["case"]["seed"] == "C"
    assert "npc_semantic" in state
    assert "investigation" in state
    assert "dialogue" in state
    assert "learning" in state
    assert "debug" not in state


def test_runner_initializes_mbam_runtime_npc_states(tmp_path: Path):
    _state, runner = _export_single_tick_state(tmp_path, channels=["WORLD"], case_seed="A")

    npc_states = runner.get_npc_states()
    assert set(npc_states.keys()) == {"elodie", "marc", "samira", "laurent", "jo"}
    assert npc_states["elodie"].current_room_id == "MBAM_LOBBY"
    assert npc_states["marc"].current_room_id == "SECURITY_OFFICE"
    assert npc_states["marc"].overlay_role_slot == "ALLY"
    assert runner.get_npc_state("jo") is not None


def test_runner_applies_seeded_overlays_to_runtime_npc_state(tmp_path: Path):
    _state_a, runner_a = _export_single_tick_state(tmp_path, channels=["WORLD"], case_seed="A")
    _state_b, runner_b = _export_single_tick_state(tmp_path, channels=["WORLD"], case_seed="B")
    _state_c, runner_c = _export_single_tick_state(tmp_path, channels=["WORLD"], case_seed="C")

    marc_a = runner_a.get_npc_state("marc")
    marc_b = runner_b.get_npc_state("marc")
    marc_c = runner_c.get_npc_state("marc")
    samira_b = runner_b.get_npc_state("samira")
    laurent_c = runner_c.get_npc_state("laurent")
    elodie_a = runner_a.get_npc_state("elodie")

    assert marc_a is not None and marc_a.overlay_role_slot == "ALLY"
    assert marc_b is not None and marc_b.overlay_role_slot == "GUARD"
    assert marc_c is not None and marc_c.overlay_role_slot == "GUARD"
    assert samira_b is not None and samira_b.overlay_role_slot == "CULPRIT"
    assert laurent_c is not None and laurent_c.overlay_role_slot == "CULPRIT"
    assert elodie_a is not None and elodie_a.overlay_role_slot == "MISDIRECTOR"


def test_runner_advances_npc_timeline_state_over_time(tmp_path: Path):
    clock = TickClock(dt=1.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    runner = SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(seed=123, tick_rate_hz=tick_rate_hz_from_clock(clock), time_origin_ms=0),
        render_spec=default_render_spec(),
        channels=["WORLD"],
        offline=None,
        case_config=MbamCaseConfig(seed="A"),
    )

    runner.run(num_ticks=605)

    elodie = runner.get_npc_state("elodie")
    laurent = runner.get_npc_state("laurent")
    assert elodie is not None and elodie.schedule_state.current_beat_id == "T_PLUS_02_CURATOR_CONTAINMENT"
    assert laurent is not None and laurent.schedule_state.current_beat_id == "T_PLUS_10_DONOR_EVENT"
    assert laurent.current_room_id == "PHONE_REMOTE"
    investigation_state = runner.get_investigation_object_state()
    assert investigation_state is not None
    assert investigation_state.o6_badge_terminal.archived is False

    runner.run(num_ticks=300)  # reach >= T+15 for investigation timeline archive
    investigation_state_after = runner.get_investigation_object_state()
    assert investigation_state_after is not None
    assert investigation_state_after.o6_badge_terminal.archived is True


def test_runner_submit_dialogue_turn_updates_runtime_and_turn_log() -> None:
    clock = TickClock(dt=1.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    runner = SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(seed=123, tick_rate_hz=tick_rate_hz_from_clock(clock), time_origin_ms=0),
        render_spec=default_render_spec(),
        channels=["WORLD"],
        offline=None,
        case_config=MbamCaseConfig(seed="A"),
    )

    result = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="summarize_understanding",
            presented_fact_ids=("N1",),
        )
    )
    assert result is not None
    assert result.turn_result.status == "accepted"
    assert result.turn_result.code == "scene_completed"

    log_entries = runner.get_dialogue_turn_log()
    assert len(log_entries) == 1
    assert log_entries[0].scene_id == "S1"
    assert log_entries[0].code == "scene_completed"
    assert log_entries[0].presentation_source in {"adapter", "fallback"}
    assert log_entries[0].presentation_reason_code is not None
    assert log_entries[0].npc_utterance_text is not None
    assert isinstance(log_entries[0].presentation_metadata, tuple)
    assert len(log_entries[0].presentation_metadata) > 0

    dialogue_state = runner.get_dialogue_runtime_state()
    assert dialogue_state is not None
    completion = dict(dialogue_state.scene_completion_states)
    assert completion["S1"] == "completed"


def test_runner_replay_export_includes_dialogue_presentation_transcript_fields(tmp_path: Path) -> None:
    clock = TickClock(dt=1.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    run_root = tmp_path / "run_dialogue_presentation_replay"
    runner = SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(seed=123, tick_rate_hz=tick_rate_hz_from_clock(clock), time_origin_ms=0),
        render_spec=default_render_spec(),
        channels=["WORLD", "DEBUG"],
        offline=OfflineExportConfig(
            run_root=run_root,
            channels=["WORLD", "DEBUG"],
            keyframe_ticks=[1],
            validate=False,
        ),
        case_config=MbamCaseConfig(seed="A"),
    )

    turn = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="ask_where",
        )
    )
    assert turn is not None
    runner.run(num_ticks=1)

    manifest = ManifestV0_1.from_dict(json.loads((run_root / "manifest.kvp.json").read_text("utf-8")))
    snap_ptr = manifest.snapshots[manifest.available_start_tick]
    env = read_record(run_root / snap_ptr.rel_path)
    state = env["payload"]["state"]
    visible_turn = state["dialogue"]["recent_turns"][-1]
    debug_turn = state["debug"]["dialogue_private"]["recent_turns"][-1]

    assert visible_turn["presentation_source"] in {"adapter", "fallback"}
    assert visible_turn["presentation_reason_code"] is not None
    assert isinstance(visible_turn["npc_utterance_text"], str) and visible_turn["npc_utterance_text"]
    assert isinstance(visible_turn["presentation_metadata"], list)
    assert len(visible_turn["presentation_metadata"]) > 0
    assert "mode:" in " ".join(visible_turn["presentation_metadata"])
    assert debug_turn["presentation_source"] == visible_turn["presentation_source"]
    assert debug_turn["npc_utterance_text"] == visible_turn["npc_utterance_text"]


def test_runner_case_outcome_evaluation_and_manual_action_flags() -> None:
    clock = TickClock(dt=1.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    runner = SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(seed=123, tick_rate_hz=tick_rate_hz_from_clock(clock), time_origin_ms=0),
        render_spec=default_render_spec(),
        channels=["WORLD"],
        offline=None,
        case_config=MbamCaseConfig(seed="A"),
    )

    baseline = runner.get_case_outcome_evaluation()
    assert baseline is not None
    assert baseline.primary_outcome == "in_progress"

    runner.record_case_action_flags("action:wrong_accusation")
    softened = runner.get_case_outcome_evaluation()
    assert softened is not None
    assert softened.soft_fail.triggered is True
    assert softened.primary_outcome == "soft_fail"


def test_runner_latches_soft_fail_branch_during_tick_progression() -> None:
    clock = TickClock(dt=1.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    runner = SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(seed=123, tick_rate_hz=tick_rate_hz_from_clock(clock), time_origin_ms=0),
        render_spec=default_render_spec(),
        channels=["WORLD"],
        offline=None,
        case_config=MbamCaseConfig(seed="A"),
    )
    runner.run(num_ticks=1201)

    outcome = runner.get_case_outcome_evaluation()
    assert outcome is not None
    assert outcome.soft_fail.triggered is True
    assert "outcome:soft_fail_latched" in outcome.debug_outcome_flags
    assert "item_leaves_building" in outcome.debug_outcome_flags
    assert "outcome:item_left_building" in outcome.debug_outcome_flags

    object_state = runner.get_investigation_object_state()
    assert object_state is not None
    assert object_state.o2_medallion.status == "missing"
    assert object_state.o2_medallion.location == "unknown"


def test_runner_exports_terminal_recap_after_soft_fail_tick(tmp_path: Path) -> None:
    state, _runner = _export_single_tick_state(tmp_path, channels=["WORLD"], case_seed="A")
    assert "case_recap" in state
    assert state["case_recap"]["available"] is False

    clock = TickClock(dt=1.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    run_root = tmp_path / "run_recap_terminal_soft_fail"
    runner = SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(seed=123, tick_rate_hz=tick_rate_hz_from_clock(clock), time_origin_ms=0),
        render_spec=default_render_spec(),
        channels=["WORLD"],
        offline=OfflineExportConfig(
            run_root=run_root,
            channels=["WORLD"],
            keyframe_ticks=[1201],
            validate=False,
        ),
        case_config=MbamCaseConfig(seed="A"),
    )
    runner.run(num_ticks=1201)

    manifest = ManifestV0_1.from_dict(json.loads((run_root / "manifest.kvp.json").read_text("utf-8")))
    snap_ptr = manifest.snapshots[1201]
    env = read_record(run_root / snap_ptr.rel_path)
    terminal_state = env["payload"]["state"]
    recap = terminal_state["case_recap"]
    assert recap["available"] is True
    assert recap["final_outcome_type"] == "soft_fail"
    assert recap["resolution_path"] == "soft_fail"
    assert "clock:post_T_PLUS_20_without_recovery" in recap["soft_fail"]["trigger_conditions"]


def test_runner_completion_flow_apis_are_wired_and_case_gated() -> None:
    clock = TickClock(dt=1.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    runner = SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(seed=123, tick_rate_hz=tick_rate_hz_from_clock(clock), time_origin_ms=0),
        render_spec=default_render_spec(),
        channels=["WORLD"],
        offline=None,
        case_config=MbamCaseConfig(seed="A"),
    )

    recovery = runner.attempt_case_recovery()
    assert recovery is not None
    assert recovery.status == "blocked"
    assert recovery.code in {"scene_or_trust_prerequisite_missing", "recovery_prerequisites_missing"}

    accusation_invalid = runner.attempt_case_accusation(accused_id="not_a_suspect")
    assert accusation_invalid is not None
    assert accusation_invalid.status == "invalid"
    assert accusation_invalid.code == "invalid_accused_id"

    accusation = runner.attempt_case_accusation(accused_id="samira")
    assert accusation is not None
    assert accusation.status in {"blocked", "completed"}


def test_runner_exports_learning_recent_outcomes_after_dialogue_turn(tmp_path: Path) -> None:
    clock = TickClock(dt=1.0 / 30.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    run_root = tmp_path / "run_learning_recent_outcomes"
    runner = SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=321,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(seed=321, tick_rate_hz=tick_rate_hz_from_clock(clock), time_origin_ms=0),
        render_spec=default_render_spec(),
        channels=["WORLD", "DEBUG"],
        offline=OfflineExportConfig(
            run_root=run_root,
            channels=["WORLD", "DEBUG"],
            keyframe_ticks=[1],
            validate=False,
        ),
        case_config=MbamCaseConfig(seed="A"),
    )

    result = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="summarize_understanding",
            presented_fact_ids=("N1",),
        )
    )
    assert result is not None
    assert result.turn_result.status == "accepted"
    runner.run(num_ticks=1)

    manifest = ManifestV0_1.from_dict(json.loads((run_root / "manifest.kvp.json").read_text("utf-8")))
    snap_ptr = manifest.snapshots[manifest.available_start_tick]
    env = read_record(run_root / snap_ptr.rel_path)
    state = env["payload"]["state"]

    outcomes = state["learning"]["recent_outcomes"]
    assert any(row.get("kind") == "summary_check" and row.get("code") == "summary_passed" for row in outcomes)
    assert state["learning"] == state["dialogue"]["learning"]
    assert "learning_private" in state["debug"]
