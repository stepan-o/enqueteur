import json
import uuid
from pathlib import Path
import pytest

from backend.sim4.integration.kvp_version import KVP_VERSION
from backend.sim4.integration.schema_version import INTEGRATION_SCHEMA_VERSION
from backend.sim4.integration.run_anchors import RunAnchors
from backend.sim4.integration.render_spec import (
    RenderSpec,
    CoordSystem,
    AxisSpec,
    Vec2,
    Bounds,
    ProjectionSpec,
    ZLayerSpec,
    DrawOrderSpec,
    LocalSortKeySpec,
    AssetResolutionSpec,
)
from backend.sim4.integration.manifest_schema import (
    ManifestV0_1,
    RecordPointer,
    DiffInventory,
    IntegritySpec,
)
from backend.sim4.integration.manifest_writer import write_manifest


def _anchors() -> RunAnchors:
    return RunAnchors.from_dict(
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
    )


def _render_spec() -> RenderSpec:
    d = {
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
    return RenderSpec.from_dict(d)


def _sha(idx: int) -> str:
    # produce a deterministic lowercase sha256-looking hex
    return ("%064x" % idx)


def _minimal_valid_manifest(
    start_tick=0,
    end_tick=3,
    keyframe_ticks=None,
):
    if keyframe_ticks is None:
        keyframe_ticks = [0, 2]

    # Build pointers
    snapshots = {}
    integrity_map = {}
    for i, t in enumerate(keyframe_ticks):
        rp = RecordPointer(
            id=f"snap-{t}",
            rel_path=f"state/snapshots/{t}.json",
            format="JSON",
            msg_type="FULL_SNAPSHOT",
            tick=t,
        )
        snapshots[t] = rp
        integrity_map[rp.id] = _sha(100 + i)

    diffs_map = {}
    for ft in range(start_tick, end_tick):
        rp = RecordPointer(
            id=f"diff-{ft}",
            rel_path=f"state/diffs/{ft}.json",
            format="JSON",
            msg_type="FRAME_DIFF",
            from_tick=ft,
            to_tick=ft + 1,
        )
        diffs_map[ft] = rp
        integrity_map[rp.id] = _sha(200 + ft)

    diffs = DiffInventory(diffs_by_from_tick=diffs_map)
    integrity = IntegritySpec.from_dict({"hash_alg": "SHA-256", "records_sha256": integrity_map})

    m = ManifestV0_1(
        kvp_version=KVP_VERSION,
        schema_version=INTEGRATION_SCHEMA_VERSION,
        run_anchors=_anchors(),
        render_spec=_render_spec(),
        available_start_tick=start_tick,
        available_end_tick=end_tick,
        channels=["ITEMS", "WORLD"],  # deliberately unsorted to test canonicalization
        keyframe_interval=None,
        keyframe_ticks=keyframe_ticks,
        snapshots=snapshots,
        diffs=diffs,
        integrity=integrity,
        layout=None,
        overlays=None,
    )
    return m


# --- Required fields + strict validation ---


def test_missing_render_spec_fails():
    m = _minimal_valid_manifest()
    d = m.to_dict()
    d.pop("render_spec")
    with pytest.raises(ValueError):
        ManifestV0_1.from_dict(d)


def test_missing_run_anchors_fails():
    m = _minimal_valid_manifest()
    d = m.to_dict()
    d.pop("run_anchors")
    with pytest.raises(ValueError):
        ManifestV0_1.from_dict(d)


def test_missing_tick_window_fails():
    m = _minimal_valid_manifest()
    d = m.to_dict()
    d.pop("available_start_tick")
    with pytest.raises(ValueError):
        ManifestV0_1.from_dict(d)


def test_end_tick_less_than_start_fails():
    m = _minimal_valid_manifest()
    d = m.to_dict()
    d["available_end_tick"] = -1
    with pytest.raises(ValueError):
        ManifestV0_1.from_dict(d)


# --- Keyframe policy enforcement ---


def test_both_keyframe_policies_present_fails():
    m = _minimal_valid_manifest()
    d = m.to_dict()
    d["keyframe_interval"] = 2
    with pytest.raises(ValueError):
        ManifestV0_1.from_dict(d)


def test_neither_keyframe_policy_present_fails():
    m = _minimal_valid_manifest()
    d = m.to_dict()
    d.pop("keyframe_ticks", None)
    with pytest.raises(ValueError):
        ManifestV0_1.from_dict(d)


def test_keyframe_ticks_unsorted_or_duplicates_fail():
    m = _minimal_valid_manifest(keyframe_ticks=[2, 0])
    with pytest.raises(ValueError):
        m.validate()
    # duplicates
    with pytest.raises(ValueError):
        _minimal_valid_manifest(keyframe_ticks=[0, 0, 2]).validate()


def test_keyframe_ticks_outside_window_fail():
    m = _minimal_valid_manifest(start_tick=0, end_tick=3, keyframe_ticks=[0, 4])
    with pytest.raises(ValueError):
        m.validate()


# --- Channel set rules ---


def test_channels_rules_and_canonicalization():
    m = _minimal_valid_manifest()
    # canonicalization on serialization
    d = m.to_dict()
    assert d["channels"] == sorted(d["channels"])  # sorted order

    # empty -> fail
    bad = m.to_dict()
    bad["channels"] = []
    with pytest.raises(ValueError):
        ManifestV0_1.from_dict(bad)

    # duplicates -> fail
    bad = m.to_dict()
    bad["channels"] = ["WORLD", "WORLD"]
    with pytest.raises(ValueError):
        ManifestV0_1.from_dict(bad)

    # unknown channel -> fail
    bad = m.to_dict()
    bad["channels"] = ["WORLD", "ALIENS"]
    with pytest.raises(ValueError):
        ManifestV0_1.from_dict(bad)


# --- Inventory discoverability ---


def test_missing_snapshot_for_keyframe_fails():
    m = _minimal_valid_manifest(keyframe_ticks=[0, 2])
    # remove snapshot at tick 2
    snapshots = dict(m.snapshots)
    snapshots.pop(2)
    m2 = ManifestV0_1(
        kvp_version=m.kvp_version,
        schema_version=m.schema_version,
        run_anchors=m.run_anchors,
        render_spec=m.render_spec,
        available_start_tick=m.available_start_tick,
        available_end_tick=m.available_end_tick,
        channels=m.channels,
        keyframe_interval=None,
        keyframe_ticks=[0, 2],
        snapshots=snapshots,
        diffs=m.diffs,
        integrity=m.integrity,
    )
    with pytest.raises(ValueError):
        m2.validate()


def test_missing_diff_transition_fails():
    m = _minimal_valid_manifest(start_tick=0, end_tick=3)
    # remove diff for from_tick=1
    diffs_map = dict(m.diffs.diffs_by_from_tick)
    diffs_map.pop(1)
    m2 = ManifestV0_1(
        kvp_version=m.kvp_version,
        schema_version=m.schema_version,
        run_anchors=m.run_anchors,
        render_spec=m.render_spec,
        available_start_tick=m.available_start_tick,
        available_end_tick=m.available_end_tick,
        channels=m.channels,
        keyframe_interval=None,
        keyframe_ticks=m.keyframe_ticks,
        snapshots=m.snapshots,
        diffs=DiffInventory(diffs_by_from_tick=diffs_map),
        integrity=m.integrity,
    )
    with pytest.raises(ValueError):
        m2.validate()


# --- Integrity coverage ---


def test_missing_integrity_entry_fails():
    m = _minimal_valid_manifest()
    # remove integrity for a diff pointer
    ptr = next(iter(m.diffs.diffs_by_from_tick.values()))
    integ_map = dict(m.integrity.records_sha256)
    integ_map.pop(ptr.id, None)
    bad = ManifestV0_1(
        kvp_version=m.kvp_version,
        schema_version=m.schema_version,
        run_anchors=m.run_anchors,
        render_spec=m.render_spec,
        available_start_tick=m.available_start_tick,
        available_end_tick=m.available_end_tick,
        channels=m.channels,
        keyframe_interval=None,
        keyframe_ticks=m.keyframe_ticks,
        snapshots=m.snapshots,
        diffs=m.diffs,
        integrity=IntegritySpec.from_dict({"hash_alg": "SHA-256", "records_sha256": integ_map}),
    )
    with pytest.raises(ValueError):
        bad.validate()


# --- Writer round-trip ---


def test_writer_round_trip(tmp_path: Path):
    m = _minimal_valid_manifest()
    f = tmp_path / "manifest.kvp.json"
    write_manifest(f, m)
    raw = f.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")  # no BOM
    d = json.loads(raw.decode("utf-8"))
    m2 = ManifestV0_1.from_dict(d)
    assert m.to_dict() == m2.to_dict()
