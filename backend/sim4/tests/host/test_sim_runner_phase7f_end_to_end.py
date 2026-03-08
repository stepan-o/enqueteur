from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from backend.sim4.case_mbam import (
    DialogueTurnRequest,
    DialogueTurnSlotValue,
    build_visible_outcome_projection,
    build_visible_run_recap_projection,
    make_investigation_command,
)
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.host.kvp_defaults import (
    default_render_spec,
    default_run_anchors,
    tick_rate_hz_from_clock,
)
from backend.sim4.host.sim_runner import MbamCaseConfig, OfflineExportConfig, SimRunner
from backend.sim4.integration.manifest_schema import ManifestV0_1
from backend.sim4.integration.record_writer import read_record
from backend.sim4.runtime.clock import TickClock
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


class _NoopScheduler:
    def iter_phase_systems(self, phase: str):  # noqa: ARG002
        return ()


def _make_runner(
    *,
    seed: str,
    offline_run_root: Path | None = None,
    channels: tuple[str, ...] = ("WORLD",),
    offline_keyframe_ticks: tuple[int, ...] = (1,),
) -> SimRunner:
    clock = TickClock(dt=1.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)

    offline = None
    if offline_run_root is not None:
        offline = OfflineExportConfig(
            run_root=offline_run_root,
            channels=list(channels),
            keyframe_ticks=list(offline_keyframe_ticks),
            validate=False,
        )

    return SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(
            seed=123,
            tick_rate_hz=tick_rate_hz_from_clock(clock),
            time_origin_ms=0,
        ),
        render_spec=default_render_spec(),
        channels=list(channels),
        offline=offline,
        case_config=MbamCaseConfig(seed=seed),
    )


def _inject_confrontation_gate_state(
    runner: SimRunner,
    *,
    elodie_trust: float = 0.95,
) -> None:
    runtime = runner.get_dialogue_runtime_state()
    assert runtime is not None
    completion_map = dict(runtime.scene_completion_states)
    completion_map["S5"] = "available"
    surfaced = set(runtime.surfaced_scene_ids).union({"S5"})
    runner._dialogue_runtime_state = replace(  # type: ignore[attr-defined]
        runtime,
        scene_completion_states=tuple((scene_id, completion_map[scene_id]) for scene_id, _state in runtime.scene_completion_states),
        surfaced_scene_ids=tuple(scene_id for scene_id, _state in runtime.scene_completion_states if scene_id in surfaced),
    )

    npc_states = runner.get_npc_states()
    assert "elodie" in npc_states
    npc_states["elodie"] = replace(npc_states["elodie"], trust=elodie_trust)
    runner._npc_states = npc_states  # type: ignore[attr-defined]


def _inject_progress_overrides(
    runner: SimRunner,
    *,
    fact_ids: tuple[str, ...] = (),
    discovered_evidence_ids: tuple[str, ...] = (),
    collected_evidence_ids: tuple[str, ...] = (),
) -> None:
    progress = runner.get_investigation_progress()
    assert progress is not None
    runner._investigation_progress = replace(  # type: ignore[attr-defined]
        progress,
        known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union(fact_ids))),
        discovered_evidence_ids=tuple(sorted(set(progress.discovered_evidence_ids).union(discovered_evidence_ids))),
        collected_evidence_ids=tuple(sorted(set(progress.collected_evidence_ids).union(collected_evidence_ids))),
    )


def _run_accusation_sequence_with_mg_proxies(runner: SimRunner, *, include_contradiction: bool) -> None:
    # MG1 proxy: label read
    mg1 = runner.submit_investigation_command(
        make_investigation_command(object_id="O3_WALL_LABEL", affordance_id="read"),
    )
    assert mg1 is not None and mg1.ack.kind == "success"

    # MG4 proxy: torn-note source interaction
    mg4 = runner.submit_investigation_command(
        make_investigation_command(object_id="O4_BENCH", affordance_id="inspect"),
    )
    assert mg4 is not None and mg4.ack.kind == "success"

    # MG2 proxy: security log flow -> N3
    access = runner.submit_investigation_command(
        make_investigation_command(object_id="O6_BADGE_TERMINAL", affordance_id="request_access"),
        available_prerequisites=("scene:S2", "trust:marc>=gate"),
    )
    assert access is not None and access.ack.kind == "success"

    logs = runner.submit_investigation_command(
        make_investigation_command(object_id="O6_BADGE_TERMINAL", affordance_id="view_logs"),
        available_prerequisites=("access:terminal_granted",),
    )
    assert logs is not None and logs.ack.kind == "success"

    # MG3 proxy: receipt flow -> E2 + N4
    receipt_ask = runner.submit_investigation_command(
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="ask_for_receipt"),
        available_prerequisites=("scene:S4",),
    )
    assert receipt_ask is not None and receipt_ask.ack.kind == "success"

    receipt_read = runner.submit_investigation_command(
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="read_receipt"),
        available_prerequisites=("inventory:E2_CAFE_RECEIPT",),
    )
    assert receipt_read is not None and receipt_read.ack.kind == "success"

    # Dialogue sequence: reveal N5 and register two accepted summaries.
    who_turn = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S3",
            npc_id="samira",
            intent_id="ask_who",
            provided_slots=(DialogueTurnSlotValue(slot_name="time", value="17h58"),),
        )
    )
    assert who_turn is not None and who_turn.turn_result.status == "accepted"

    reassure_1 = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="reassure",
        )
    )
    assert reassure_1 is not None and reassure_1.turn_result.status == "accepted"

    reassure_2 = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="reassure",
        )
    )
    assert reassure_2 is not None and reassure_2.turn_result.status == "accepted"

    s1_summary = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="summarize_understanding",
            presented_fact_ids=("N1",),
        )
    )
    assert s1_summary is not None and s1_summary.turn_result.status == "accepted"
    assert s1_summary.summary_check is not None and s1_summary.summary_check.code == "summary_passed"

    s3_summary = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S3",
            npc_id="samira",
            intent_id="summarize_understanding",
            provided_slots=(DialogueTurnSlotValue(slot_name="time", value="17h58"),),
            presented_fact_ids=("N3",),
        )
    )
    assert s3_summary is not None and s3_summary.turn_result.status == "accepted"
    assert s3_summary.summary_check is not None and s3_summary.summary_check.code == "summary_passed"

    if include_contradiction:
        contradiction = runner.submit_contradiction_edge(edge_id="E3")
        assert contradiction is not None
        assert contradiction.status == "success"


def _run_seed_c_accusation_success_sequence() -> tuple[dict, dict]:
    runner = _make_runner(seed="C")
    _run_accusation_sequence_with_mg_proxies(runner, include_contradiction=True)
    _inject_confrontation_gate_state(runner)

    completion = runner.attempt_case_accusation(accused_id="laurent")
    assert completion is not None and completion.status == "completed"

    outcome = runner.get_case_outcome_evaluation()
    assert outcome is not None
    return build_visible_outcome_projection(outcome), build_visible_run_recap_projection(outcome)


def test_phase7f_end_to_end_recovery_success_seed_a() -> None:
    runner = _make_runner(seed="A")

    for _ in range(8):
        reassure = runner.submit_dialogue_turn(
            DialogueTurnRequest(
                scene_id="S1",
                npc_id="elodie",
                intent_id="reassure",
            )
        )
        assert reassure is not None and reassure.turn_result.status == "accepted"

    s1_summary = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="summarize_understanding",
            presented_fact_ids=("N1",),
        )
    )
    assert s1_summary is not None and s1_summary.turn_result.status == "accepted"

    n2 = runner.submit_investigation_command(
        make_investigation_command(object_id="O8_KEYPAD_DOOR", affordance_id="inspect"),
    )
    assert n2 is not None and n2.ack.kind in {"success", "no_op"}

    n3 = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S3",
            npc_id="samira",
            intent_id="ask_when",
            provided_slots=(DialogueTurnSlotValue(slot_name="time", value="17h58"),),
        )
    )
    assert n3 is not None and n3.turn_result.status == "accepted"

    # S4 is time-gated to T+08..T+18; advance deterministically into the window.
    runner.run(num_ticks=480)

    n4 = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S4",
            npc_id="jo",
            intent_id="ask_when",
            provided_slots=(DialogueTurnSlotValue(slot_name="time", value="17h52"),),
        )
    )
    assert n4 is not None and n4.turn_result.status == "accepted"

    ask = runner.submit_investigation_command(
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="ask_for_receipt"),
    )
    assert ask is not None and ask.ack.kind == "success"
    read = runner.submit_investigation_command(
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="read_receipt"),
    )
    assert read is not None and read.ack.kind == "success"

    contradiction = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S3",
            npc_id="samira",
            intent_id="challenge_contradiction",
            provided_slots=(DialogueTurnSlotValue(slot_name="time", value="17h58"),),
            presented_fact_ids=("N3", "N4"),
            presented_evidence_ids=("E2_CAFE_RECEIPT",),
        )
    )
    assert contradiction is not None and contradiction.turn_result.status == "accepted"
    assert "N8" in contradiction.turn_result.revealed_fact_ids

    s3_summary = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S3",
            npc_id="samira",
            intent_id="summarize_understanding",
            provided_slots=(DialogueTurnSlotValue(slot_name="time", value="17h58"),),
            presented_fact_ids=("N3",),
        )
    )
    assert s3_summary is not None and s3_summary.turn_result.status == "accepted"

    trace = runner.submit_investigation_command(
        make_investigation_command(object_id="O1_DISPLAY_CASE", affordance_id="examine_surface"),
    )
    assert trace is not None and trace.ack.kind == "success"
    assert "E3_METHOD_TRACE" in trace.revealed_evidence_ids

    recovery = runner.attempt_case_recovery(quiet=True)
    assert recovery is not None
    assert recovery.status == "completed"
    assert recovery.code == "recovery_success_completed"

    outcome = runner.get_case_outcome_evaluation()
    assert outcome is not None
    recap = build_visible_run_recap_projection(outcome)
    assert outcome.primary_outcome == "recovery_success"
    assert outcome.recovery_success.satisfied is True
    assert recap["final_outcome_type"] == "recovery_success"
    assert recap["resolution_path"] == "recovery"


def test_phase7f_end_to_end_accusation_success_seed_c_with_contradiction_enforcement() -> None:
    runner = _make_runner(seed="C")
    _run_accusation_sequence_with_mg_proxies(runner, include_contradiction=False)

    # First accusation must fail before contradiction action is recorded.
    blocked = runner.attempt_case_accusation(accused_id="laurent")
    assert blocked is not None
    assert blocked.status == "blocked"
    assert "action:state_contradiction_N3_N4" in blocked.missing_action_flags

    contradiction = runner.submit_contradiction_edge(edge_id="E3")
    assert contradiction is not None
    assert contradiction.status == "success"
    assert contradiction.action_flag == "action:state_contradiction_N3_N4"

    completed = runner.attempt_case_accusation(accused_id="laurent")
    assert completed is not None
    assert completed.status == "completed"
    assert completed.code == "accusation_success_completed"

    outcome = runner.get_case_outcome_evaluation()
    assert outcome is not None
    recap = build_visible_run_recap_projection(outcome)
    assert outcome.primary_outcome == "accusation_success"
    assert outcome.accusation_success.satisfied is True
    assert outcome.contradiction_requirement_satisfied is True
    assert recap["final_outcome_type"] == "accusation_success"
    assert recap["resolution_path"] == "accusation"


def test_phase7f_end_to_end_soft_fail_seed_b_wrong_accusation() -> None:
    runner = _make_runner(seed="B")
    _inject_confrontation_gate_state(runner)

    wrong = runner.attempt_case_accusation(accused_id="laurent", public=True)
    assert wrong is not None
    assert wrong.status == "completed"
    assert wrong.code == "wrong_accusation_soft_fail"

    outcome = runner.get_case_outcome_evaluation()
    assert outcome is not None
    recap = build_visible_run_recap_projection(outcome)
    assert outcome.primary_outcome == "soft_fail"
    assert outcome.soft_fail.triggered is True
    assert recap["final_outcome_type"] == "soft_fail"
    assert recap["resolution_path"] == "soft_fail"
    assert recap["soft_fail"]["triggered"] is True


def test_phase7f_same_seed_same_sequence_is_deterministic_for_outcome_and_recap() -> None:
    first_outcome, first_recap = _run_seed_c_accusation_success_sequence()
    second_outcome, second_recap = _run_seed_c_accusation_success_sequence()
    assert first_outcome == second_outcome
    assert first_recap == second_recap


def test_phase7f_replay_export_reconstructs_terminal_full_run_state(tmp_path: Path) -> None:
    run_root = tmp_path / "phase7f_seed_b_soft_fail_replay"
    runner = _make_runner(
        seed="B",
        offline_run_root=run_root,
        channels=("WORLD", "DEBUG"),
        offline_keyframe_ticks=(1, 1201),
    )

    # Pure tick-driven terminal branch: soft-fail by elapsed clock > T+20.
    runner.run(num_ticks=1201)

    manifest = ManifestV0_1.from_dict(json.loads((run_root / "manifest.kvp.json").read_text("utf-8")))
    terminal_ptr = manifest.snapshots[manifest.available_end_tick]
    env = read_record(run_root / terminal_ptr.rel_path)
    reconstructed = env["payload"]["state"]

    assert reconstructed["case"]["case_id"] == "MBAM_01"
    assert reconstructed["case"]["seed"] == "B"
    assert reconstructed["case_outcome"]["primary_outcome"] == "soft_fail"
    assert reconstructed["case_outcome"]["terminal"] is True
    assert reconstructed["case_recap"]["available"] is True
    assert reconstructed["case_recap"]["final_outcome_type"] == "soft_fail"
    assert reconstructed["case_recap"]["resolution_path"] == "soft_fail"


def test_phase7g_dialogue_turn_updates_runtime_npc_trust_and_stress() -> None:
    runner = _make_runner(seed="C")
    npc_before = runner.get_npc_state("elodie")
    assert npc_before is not None

    result = runner.submit_dialogue_turn(
        DialogueTurnRequest(
            scene_id="S1",
            npc_id="elodie",
            intent_id="reassure",
        )
    )
    assert result is not None
    assert result.turn_result.status == "accepted"
    assert result.turn_result.trust_delta > 0.0
    assert result.turn_result.stress_delta < 0.0

    npc_after = runner.get_npc_state("elodie")
    assert npc_after is not None
    assert npc_after.trust > npc_before.trust
    assert npc_after.stress < npc_before.stress


def test_phase7g_runner_derives_runtime_prerequisites_for_receipt_read_flow() -> None:
    runner = _make_runner(seed="B")

    ask = runner.submit_investigation_command(
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="ask_for_receipt"),
    )
    assert ask is not None
    assert ask.ack.kind == "success"
    assert "E2_CAFE_RECEIPT" in ask.revealed_evidence_ids

    # No explicit inventory prerequisite provided; runner should derive it
    # from deterministic progress state after ask_for_receipt.
    read = runner.submit_investigation_command(
        make_investigation_command(object_id="O9_RECEIPT_PRINTER", affordance_id="read_receipt"),
    )
    assert read is not None
    assert read.ack.kind == "success"
    assert "N4" in read.fact_unlock_candidates
