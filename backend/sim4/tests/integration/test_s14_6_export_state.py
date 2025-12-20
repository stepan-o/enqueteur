import json
import uuid
from pathlib import Path
import pytest

from backend.sim4.integration.kvp_version import KVP_VERSION
from backend.sim4.integration.schema_version import INTEGRATION_SCHEMA_VERSION
from backend.sim4.integration.manifest_schema import (
    ManifestV0_1,
    RecordPointer,
    DiffInventory,
    IntegritySpec,
)
from backend.sim4.integration.export_state import StateSource, export_state_records
from backend.sim4.integration.export_verify import reconstruct_state_at_tick
from backend.sim4.integration.record_writer import read_record, write_record


class _DummySource(StateSource):
    def get_state(self, tick: int):  # type: ignore[override]
        # Deterministic, simple state with a float to exercise quantization
        return {
            "tick": tick,
            "value": tick,
            "pos": {"x": tick + 0.123456, "y": 2.0},
            # include some list ordering that shouldn't matter to hashing after canonicalization
            "rooms": [{"room_id": "b"}, {"room_id": "a"}],
        }


def _sha_like(n: int) -> str:
    return ("%064x" % n)


def _ptr_snapshot(t: int) -> RecordPointer:
    return RecordPointer(
        id=f"snap-{t}",
        rel_path=f"state/snapshots/tick_{t:010d}.kvp.json",
        format="JSON",
        msg_type="FULL_SNAPSHOT",
        tick=t,
    )


def _ptr_diff(f: int) -> RecordPointer:
    return RecordPointer(
        id=f"diff-{f}",
        rel_path=f"state/diffs/from_{f:010d}_to_{f+1:010d}.kvp.json",
        format="JSON",
        msg_type="FRAME_DIFF",
        from_tick=f,
        to_tick=f + 1,
    )


def _build_manifest(start_tick=0, end_tick=4, keyframe_ticks=(0, 2)) -> ManifestV0_1:
    snaps = {}
    diffs = {}
    integ = {}

    for i, t in enumerate(keyframe_ticks):
        rp = _ptr_snapshot(t)
        snaps[t] = rp
        integ[rp.id] = _sha_like(100 + i)

    for ft in range(start_tick, end_tick):
        rp = _ptr_diff(ft)
        diffs[ft] = rp
        integ[rp.id] = _sha_like(1000 + ft)

    return ManifestV0_1(
        kvp_version=KVP_VERSION,
        schema_version=INTEGRATION_SCHEMA_VERSION,
        run_anchors=__import__(
            "backend.sim4.integration.run_anchors", fromlist=["RunAnchors"]
        ).RunAnchors.from_dict(
            {
                "engine_name": "Sim4",
                "engine_version": "1.0.0",
                "schema_version": INTEGRATION_SCHEMA_VERSION,
                "world_id": str(uuid.uuid4()),
                "run_id": str(uuid.uuid4()),
                "seed": 1,
                "tick_rate_hz": 30,
                "time_origin_ms": 0,
            }
        ),
        render_spec=__import__(
            "backend.sim4.integration.render_spec", fromlist=["RenderSpec"]
        ).RenderSpec.from_dict(
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
        available_start_tick=start_tick,
        available_end_tick=end_tick,
        channels=["WORLD"],
        keyframe_interval=None,
        keyframe_ticks=list(keyframe_ticks),
        snapshots=snaps,
        diffs=DiffInventory(diffs_by_from_tick=diffs),
        integrity=IntegritySpec.from_dict({"hash_alg": "SHA-256", "records_sha256": integ}),
        layout=None,
        overlays=None,
    )


def test_export_and_verify_round_trip(tmp_path: Path):
    manifest = _build_manifest(start_tick=0, end_tick=4, keyframe_ticks=(0, 2))
    source = _DummySource()
    export_root = tmp_path

    # write records
    export_state_records(export_root, manifest, source)

    # Verify reconstruction at various ticks
    s0 = reconstruct_state_at_tick(export_root, manifest, 0)
    assert s0["tick"] == 0
    s3 = reconstruct_state_at_tick(export_root, manifest, 3)
    assert s3["tick"] == 3
    s2 = reconstruct_state_at_tick(export_root, manifest, 2)
    assert s2["tick"] == 2


def test_broken_hash_chain_fails(tmp_path: Path):
    manifest = _build_manifest(start_tick=0, end_tick=2, keyframe_ticks=(0,))
    source = _DummySource()
    export_state_records(tmp_path, manifest, source)
    # Tamper with diff prev_step_hash
    diff_path = tmp_path / manifest.diffs.diffs_by_from_tick[0].rel_path
    env = read_record(diff_path)
    env["payload"]["prev_step_hash"] = "0" * 64
    write_record(diff_path, env)
    with pytest.raises(ValueError):
        reconstruct_state_at_tick(tmp_path, manifest, 1)


def test_missing_diff_file_fails(tmp_path: Path):
    manifest = _build_manifest(start_tick=0, end_tick=2, keyframe_ticks=(0,))
    source = _DummySource()
    export_state_records(tmp_path, manifest, source)
    diff_path = tmp_path / manifest.diffs.diffs_by_from_tick[0].rel_path
    diff_path.unlink()
    with pytest.raises(Exception):
        reconstruct_state_at_tick(tmp_path, manifest, 1)


def test_wrong_to_tick_in_diff_payload_fails(tmp_path: Path):
    manifest = _build_manifest(start_tick=0, end_tick=2, keyframe_ticks=(0,))
    source = _DummySource()
    export_state_records(tmp_path, manifest, source)
    diff_path = tmp_path / manifest.diffs.diffs_by_from_tick[0].rel_path
    env = read_record(diff_path)
    env["payload"]["to_tick"] = env["payload"]["from_tick"] + 2
    write_record(diff_path, env)
    with pytest.raises(ValueError):
        reconstruct_state_at_tick(tmp_path, manifest, 1)


def test_missing_schema_version_in_snapshot_fails(tmp_path: Path):
    manifest = _build_manifest(start_tick=0, end_tick=1, keyframe_ticks=(0,))
    source = _DummySource()
    export_state_records(tmp_path, manifest, source)
    snap_path = tmp_path / manifest.snapshots[0].rel_path
    env = read_record(snap_path)
    env["payload"].pop("schema_version", None)
    write_record(snap_path, env)
    with pytest.raises(ValueError):
        reconstruct_state_at_tick(tmp_path, manifest, 0)
