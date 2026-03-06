from __future__ import annotations

import json
import random
from dataclasses import asdict
from pathlib import Path

import pytest

from backend.sim4.case_mbam import (
    build_debug_case_projection,
    build_visible_case_projection,
    generate_case_state_for_seed_id,
)
from backend.sim4.integration.export_state import export_state_records
from backend.sim4.integration.kvp_version import KVP_VERSION
from backend.sim4.integration.kvp_state_history import KvpStateHistory
from backend.sim4.integration.manifest_schema import (
    DiffInventory,
    IntegritySpec,
    ManifestV0_1,
    RecordPointer,
)
from backend.sim4.integration.record_writer import read_record
from backend.sim4.integration.render_spec import RenderSpec
from backend.sim4.integration.run_anchors import RunAnchors
from backend.sim4.integration.schema_version import INTEGRATION_SCHEMA_VERSION
from backend.sim4.snapshot.world_snapshot import WorldSnapshot


def _state_fingerprint(seed_id: str) -> str:
    state = generate_case_state_for_seed_id(seed_id)  # type: ignore[arg-type]
    # JSON fingerprint gives explicit byte-stable representation for equality checks.
    return json.dumps(asdict(state), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sample_world_snapshot(*, tick_index: int) -> WorldSnapshot:
    return WorldSnapshot(
        world_id=0,
        tick_index=tick_index,
        episode_id=0,
        time_seconds=float(tick_index),
        day_index=1,
        ticks_per_day=60,
        tick_in_day=tick_index,
        time_of_day=float(tick_index) / 60.0,
        day_phase="day",
        phase_progress=0.0,
        world_output=0.0,
        rooms=[],
        agents=[],
        items=[],
        objects=[],
        doors=[],
        room_index={},
        agent_index={},
    )


def _manifest_for_single_tick(tick_index: int) -> ManifestV0_1:
    snap_ptr = RecordPointer(
        id=f"snap-{tick_index}",
        rel_path=f"state/snapshots/tick_{tick_index:010d}.kvp.json",
        format="JSON",
        msg_type="FULL_SNAPSHOT",
        tick=tick_index,
    )
    return ManifestV0_1(
        kvp_version=KVP_VERSION,
        schema_version=INTEGRATION_SCHEMA_VERSION,
        run_anchors=RunAnchors.from_dict(
            {
                "engine_name": "EnqueteurSim",
                "engine_version": "1.0.0",
                "schema_version": INTEGRATION_SCHEMA_VERSION,
                "world_id": "00000000-0000-4000-8000-000000000101",
                "run_id": "00000000-0000-4000-8000-000000000202",
                "seed": 1,
                "tick_rate_hz": 30,
                "time_origin_ms": 0,
            }
        ),
        render_spec=RenderSpec.from_dict(
            {
                "coord_system": {
                    "units": "meters",
                    "units_per_tile": 1.0,
                    "axis": {"x_positive": "right", "y_positive": "down"},
                    "origin": {"x": 0.0, "y": 0.0},
                    "bounds": {"min_x": 0.0, "min_y": 0.0, "max_x": 10.0, "max_y": 5.0},
                },
                "projection": {"kind": "isometric", "recommended_iso_tile_w": 64, "recommended_iso_tile_h": 32},
                "z_layer": {"meaning": "tile", "stable_across_run": True, "notes": None},
                "draw_order": {"rooms": ["floors"], "agents": ["humans"], "items": ["props"]},
                "local_sort_key": {"source": "y_then_x", "quantization": "Q1E3", "direction": "asc", "notes": None},
                "asset_resolution": {"policy": "prefer_runtime_recommended", "missing_ref_behavior": "error"},
            }
        ),
        available_start_tick=tick_index,
        available_end_tick=tick_index,
        channels=["WORLD", "DEBUG"],
        keyframe_interval=None,
        keyframe_ticks=[tick_index],
        snapshots={tick_index: snap_ptr},
        diffs=DiffInventory(diffs_by_from_tick={}),
        integrity=IntegritySpec.from_dict(
            {
                "hash_alg": "SHA-256",
                "records_sha256": {snap_ptr.id: "0" * 64},
            }
        ),
        layout=None,
        overlays=None,
    )


def test_same_seed_determinism_for_a() -> None:
    assert _state_fingerprint("A") == _state_fingerprint("A")


def test_same_seed_determinism_for_b() -> None:
    assert _state_fingerprint("B") == _state_fingerprint("B")


def test_same_seed_determinism_for_c() -> None:
    assert _state_fingerprint("C") == _state_fingerprint("C")


def test_cross_seed_variation_for_roles_and_core_outputs() -> None:
    case_a = generate_case_state_for_seed_id("A")
    case_b = generate_case_state_for_seed_id("B")
    case_c = generate_case_state_for_seed_id("C")

    assert case_a.roles_assignment.culprit == "outsider"
    assert case_b.roles_assignment.culprit == "samira"
    assert case_c.roles_assignment.culprit == "laurent"

    assert case_a.roles_assignment.method == "delivery_cart_swap"
    assert case_b.roles_assignment.method == "badge_borrow"
    assert case_c.roles_assignment.method == "case_left_unlatched"

    assert case_a.roles_assignment.ally == "marc"
    assert case_b.roles_assignment.ally == "jo"
    assert case_c.roles_assignment.ally == "elodie"

    assert case_a.evidence_placement.drop_location.location_id == "corridor_bin"
    assert case_b.evidence_placement.drop_location.location_id == "cafe_bathroom_stash"
    assert case_c.evidence_placement.drop_location.location_id == "coat_rack_pocket"

    assert case_a.evidence_placement.cafe.receipt_id != case_b.evidence_placement.cafe.receipt_id
    assert case_b.evidence_placement.cafe.receipt_id != case_c.evidence_placement.cafe.receipt_id
    assert case_a.evidence_placement.cafe.receipt_id != case_c.evidence_placement.cafe.receipt_id

    # T+10 differs by fixture (A call vs B/C appearance on site)
    donor_a = next(b for b in case_a.timeline_schedule if b.beat_id == "T_PLUS_10_DONOR_EVENT")
    donor_b = next(b for b in case_b.timeline_schedule if b.beat_id == "T_PLUS_10_DONOR_EVENT")
    donor_c = next(b for b in case_c.timeline_schedule if b.beat_id == "T_PLUS_10_DONOR_EVENT")
    assert donor_a.location_id == "PHONE_REMOTE"
    assert donor_b.location_id == "MBAM_LOBBY"
    assert donor_c.location_id == "MBAM_LOBBY"


def test_structural_validity_for_all_shipped_seeds() -> None:
    for seed_id in ("A", "B", "C"):
        case_state = generate_case_state_for_seed_id(seed_id)  # type: ignore[arg-type]

        assert case_state.case_id == "MBAM_01"
        assert case_state.seed == seed_id
        assert case_state.runtime_clock_start != ""
        assert case_state.timeline_schedule != ()
        assert case_state.truth_graph.nodes != ()
        assert case_state.truth_graph.edges != ()
        assert case_state.alibi_matrix.elodie != ()
        assert case_state.alibi_matrix.marc != ()
        assert case_state.alibi_matrix.samira != ()
        assert case_state.alibi_matrix.laurent != ()
        assert case_state.alibi_matrix.jo != ()

        # Fixed cast entries present.
        assert case_state.cast_overlay.elodie.role_slot != ""
        assert case_state.cast_overlay.marc.role_slot != ""
        assert case_state.cast_overlay.samira.role_slot != ""
        assert case_state.cast_overlay.laurent.role_slot != ""
        assert case_state.cast_overlay.jo.role_slot != ""
        assert case_state.cast_overlay.outsider.role_slot != ""

        # Locked scenes S1-S5 present.
        assert case_state.scene_gates.S1 is not None
        assert case_state.scene_gates.S2 is not None
        assert case_state.scene_gates.S3 is not None
        assert case_state.scene_gates.S4 is not None
        assert case_state.scene_gates.S5 is not None

        # Required clue nodes N1..N8 exist for every shipped seed.
        fact_ids = {n.fact_id for n in case_state.truth_graph.nodes}
        assert {"N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8"}.issubset(fact_ids)


def test_solvability_invariants_for_all_shipped_seeds() -> None:
    for seed_id in ("A", "B", "C"):
        case_state = generate_case_state_for_seed_id(seed_id)  # type: ignore[arg-type]
        culprit = case_state.roles_assignment.culprit
        rules = case_state.resolution_rules

        # Recovery path exists.
        assert rules.recovery_success.required_fact_ids != ()
        assert rules.recovery_success.required_actions != ()
        assert "action:recover_medallion" in rules.recovery_success.required_actions

        # Accusation path exists and requires contradiction usage.
        assert rules.accusation_success.required_fact_ids != ()
        assert rules.accusation_success.required_actions != ()
        assert "action:state_contradiction_N3_N4" in rules.accusation_success.required_actions
        assert f"action:accuse_{culprit}" in rules.accusation_success.required_actions

        # Soft fail branch exists.
        assert rules.soft_fail.trigger_conditions != ()
        assert rules.soft_fail.outcome_flags != ()

        # Contradiction remains encoded in truth graph and hidden flags.
        edge_relations = {(e.from_fact_id, e.to_fact_id, e.relation) for e in case_state.truth_graph.edges}
        assert ("N3", "N4", "contradicts") in edge_relations
        assert "accusation_requires_contradiction_path" in case_state.hidden_case_slice.private_overlay_flags


def test_case_projection_and_export_path_sanity(tmp_path: Path) -> None:
    tick_index = 1
    case_state = generate_case_state_for_seed_id("A")
    visible = build_visible_case_projection(case_state, truth_epoch=1)
    debug = build_debug_case_projection(case_state, truth_epoch=1)

    history = KvpStateHistory(
        channels=["WORLD", "DEBUG"],
        case_visible_projection=visible,
        case_debug_projection=debug,
    )
    history.on_tick_output(
        tick_index=tick_index,
        dt=1.0 / 30.0,
        world_snapshot=_sample_world_snapshot(tick_index=tick_index),
        runtime_events=(),
        narrative_fragments=(),
    )

    manifest = _manifest_for_single_tick(tick_index)
    export_state_records(tmp_path, manifest, history)

    record_path = tmp_path / manifest.snapshots[tick_index].rel_path
    env = read_record(record_path)
    state = env["payload"]["state"]

    assert state["case"]["case_id"] == "MBAM_01"
    assert state["case"]["seed"] == "A"
    assert state["case"]["truth_epoch"] == 1
    assert state["case"]["visible_case_slice"]["starting_scene_id"] == "S1"
    assert "case_private" in state["debug"]
    assert state["debug"]["case_private"]["roles_assignment"]["culprit"] == "outsider"


def test_case_generator_ignores_ambient_random_state() -> None:
    random.seed(101)
    first = generate_case_state_for_seed_id("B")
    random.seed(999999)
    second = generate_case_state_for_seed_id("B")
    assert first == second


def test_case_generator_does_not_call_random_module(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_random_usage(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("Unexpected random module usage in MBAM case generation")

    monkeypatch.setattr(random, "random", _raise_random_usage)
    monkeypatch.setattr(random, "randrange", _raise_random_usage)
    monkeypatch.setattr(random, "randint", _raise_random_usage)
    monkeypatch.setattr(random, "choice", _raise_random_usage)
    monkeypatch.setattr(random, "uniform", _raise_random_usage)
    monkeypatch.setattr(random, "Random", _raise_random_usage)

    # Generation should succeed without touching random.
    case_state = generate_case_state_for_seed_id("C")
    assert case_state.seed == "C"
