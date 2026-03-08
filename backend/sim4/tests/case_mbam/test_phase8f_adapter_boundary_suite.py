from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from backend.sim4.case_mbam import (
    DialogueTurnRequest,
    build_dialogue_adapter_input,
    build_dialogue_execution_context,
    build_initial_dialogue_scene_runtime,
    build_initial_investigation_progress,
    build_learning_state,
    build_safe_dialogue_adapter_context,
    execute_dialogue_turn,
    generate_case_state_for_seed_id,
    initialize_mbam_npc_states_from_case_state,
    make_dialogue_turn_log_entry,
    resolve_dialogue_adapter_output,
)
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.host.kvp_defaults import default_render_spec, default_run_anchors, tick_rate_hz_from_clock
from backend.sim4.host.sim_runner import MbamCaseConfig, OfflineExportConfig, SimRunner
from backend.sim4.integration.manifest_schema import ManifestV0_1
from backend.sim4.integration.record_writer import read_record
from backend.sim4.runtime.clock import TickClock
from backend.sim4.world.context import WorldContext
from backend.sim4.world.mbam_layout import apply_mbam_layout


class _NoopScheduler:
    def iter_phase_systems(self, phase: str):  # noqa: ARG002
        return ()


class _RaisesAdapter:
    def render_turn(self, payload):  # noqa: ANN001
        raise RuntimeError("adapter unavailable")


class _DictAdapter:
    def __init__(self, row: dict[str, object]) -> None:
        self._row = row

    def render_turn(self, payload):  # noqa: ANN001
        _ = payload
        return self._row


def _build_payload(seed: str = "A", *, intent_id: str = "ask_where"):
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
        DialogueTurnRequest(scene_id="S1", npc_id="elodie", intent_id=intent_id),
        context=context,
    )
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
    return payload


def _build_runner(
    *,
    seed: str = "A",
    dialogue_adapter_enabled: bool,
    dialogue_adapter_style: Literal["mbam_style", "deterministic"] = "deterministic",
    channels: tuple[str, ...] = ("WORLD",),
    offline: OfflineExportConfig | None = None,
) -> SimRunner:
    clock = TickClock(dt=1.0)
    ecs_world = ECSWorld()
    world_ctx = WorldContext()
    apply_mbam_layout(world_ctx)
    return SimRunner(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=_NoopScheduler(),
        run_anchors=default_run_anchors(seed=123, tick_rate_hz=tick_rate_hz_from_clock(clock), time_origin_ms=0),
        render_spec=default_render_spec(),
        channels=list(channels),
        offline=offline,
        case_config=MbamCaseConfig(
            seed=seed,
            dialogue_adapter_enabled=dialogue_adapter_enabled,
            dialogue_adapter_style=dialogue_adapter_style,
        ),
    )


def test_phase8f_allowed_fact_packaging_excludes_hidden_and_unrevealed_facts() -> None:
    payload = _build_payload("A", intent_id="ask_what_happened")
    assert "N7" in payload.allowed_fact_ids  # legal in scene but not yet revealed
    package = build_safe_dialogue_adapter_context(payload)

    assert package.legal_facts.visible_fact_ids == ("N1",)
    assert package.legal_facts.newly_revealed_fact_ids == ()
    assert tuple(row.fact_id for row in package.legal_facts.visible_fact_payloads) == ("N1",)
    assert "N7" not in package.legal_facts.visible_fact_ids
    assert "N8" not in package.legal_facts.visible_fact_ids


def test_phase8f_normalization_rejects_adversarial_output_and_falls_back_safely() -> None:
    payload = _build_payload("A", intent_id="ask_where")

    unknown_key = resolve_dialogue_adapter_output(
        payload,
        adapter=_DictAdapter(
            {
                "npc_utterance_text": "ok",
                "debug_hidden_blob": "not allowed",
            }
        ),
        adapter_enabled=True,
    )
    assert unknown_key.source == "fallback"
    assert unknown_key.reason_code == "adapter_invalid_structure"

    hidden_id_text = resolve_dialogue_adapter_output(
        payload,
        adapter=_DictAdapter(
            {
                "npc_utterance_text": "N8 est la solution finale.",
                "referenced_fact_ids": [],
            }
        ),
        adapter_enabled=True,
    )
    assert hidden_id_text.source == "fallback"
    assert hidden_id_text.reason_code == "adapter_illegal_fact_reference"
    assert "N8" not in hidden_id_text.output.npc_utterance_text

    unrevealed_row = next(row for row in payload.allowed_fact_payloads if row.fact_id not in payload.visible_fact_ids)
    hidden_fact_text = resolve_dialogue_adapter_output(
        payload,
        adapter=_DictAdapter(
            {
                "npc_utterance_text": unrevealed_row.text,
                "referenced_fact_ids": [],
            }
        ),
        adapter_enabled=True,
    )
    assert hidden_fact_text.source == "fallback"
    assert hidden_fact_text.reason_code == "adapter_illegal_fact_reference"


def test_phase8f_fallback_modes_keep_scene_progress_and_truth_state_deterministic() -> None:
    request = DialogueTurnRequest(
        scene_id="S1",
        npc_id="elodie",
        intent_id="summarize_understanding",
        presented_fact_ids=("N1",),
    )

    baseline = _build_runner(seed="A", dialogue_adapter_enabled=False)
    case_truth_before = baseline.get_case_state()
    assert case_truth_before is not None
    baseline_result = baseline.submit_dialogue_turn(request)
    assert baseline_result is not None

    failing = _build_runner(seed="A", dialogue_adapter_enabled=True)
    failing._dialogue_presentation_adapter = _RaisesAdapter()  # intentional: adversarial boundary test
    failing_case_truth_before = failing.get_case_state()
    assert failing_case_truth_before is not None
    failing_result = failing.submit_dialogue_turn(request)
    assert failing_result is not None

    assert baseline_result.turn_result.status == "accepted"
    assert failing_result.turn_result.status == baseline_result.turn_result.status
    assert failing_result.turn_result.code == baseline_result.turn_result.code
    assert failing_result.turn_result.revealed_fact_ids == baseline_result.turn_result.revealed_fact_ids

    baseline_runtime = baseline.get_dialogue_runtime_state()
    failing_runtime = failing.get_dialogue_runtime_state()
    assert baseline_runtime is not None and failing_runtime is not None
    assert failing_runtime.scene_completion_states == baseline_runtime.scene_completion_states
    assert failing_runtime.revealed_fact_ids == baseline_runtime.revealed_fact_ids

    baseline_progress = baseline.get_investigation_progress()
    failing_progress = failing.get_investigation_progress()
    assert baseline_progress is not None and failing_progress is not None
    assert failing_progress.known_fact_ids == baseline_progress.known_fact_ids
    assert failing_progress.satisfied_action_flags == baseline_progress.satisfied_action_flags

    baseline_log = baseline.get_dialogue_turn_log()[-1]
    failing_log = failing.get_dialogue_turn_log()[-1]
    assert baseline_log.presentation_source == "fallback"
    assert baseline_log.presentation_reason_code == "adapter_disabled"
    assert failing_log.presentation_source == "fallback"
    assert failing_log.presentation_reason_code == "adapter_exception"

    case_truth_after = failing.get_case_state()
    assert case_truth_after is not None
    assert case_truth_after.truth_graph == failing_case_truth_before.truth_graph


def test_phase8f_replay_projection_reconstructs_presented_dialogue_without_model_access(tmp_path: Path) -> None:
    run_root = tmp_path / "phase8f_adapter_fallback_replay"
    runner = _build_runner(
        seed="A",
        dialogue_adapter_enabled=False,
        channels=("WORLD", "DEBUG"),
        offline=OfflineExportConfig(
            run_root=run_root,
            channels=["WORLD", "DEBUG"],
            keyframe_ticks=[1],
            validate=False,
        ),
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
    in_memory = runner.get_dialogue_turn_log()[-1]

    assert visible_turn["presentation_source"] == "fallback"
    assert visible_turn["presentation_reason_code"] == "adapter_disabled"
    assert visible_turn["npc_utterance_text"] == in_memory.npc_utterance_text
    assert debug_turn["npc_utterance_text"] == visible_turn["npc_utterance_text"]
    assert debug_turn["presentation_source"] == "fallback"
