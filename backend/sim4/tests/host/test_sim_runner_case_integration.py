from __future__ import annotations

import json
from pathlib import Path

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

    assert "debug" in state
    assert "case_private" in state["debug"]
    assert state["debug"]["case_private"]["roles_assignment"]["culprit"] == "samira"


def test_runner_omits_private_case_projection_without_debug_channel(tmp_path: Path):
    state, _runner = _export_single_tick_state(tmp_path, channels=["WORLD"], case_seed="C")

    assert "case" in state
    assert state["case"]["seed"] == "C"
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
