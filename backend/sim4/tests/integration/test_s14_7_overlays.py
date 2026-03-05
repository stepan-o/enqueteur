import json
import uuid
from pathlib import Path
import pytest

from backend.sim4.integration.kvp_envelope import validate_envelope, envelope_msg_type
from backend.sim4.integration.export_overlays import (
    export_ui_events_jsonl,
    export_psycho_frames_jsonl,
)
from backend.sim4.integration.overlay_schemas import UIEventBatch, PsychoFrame
from backend.sim4.integration.manifest_schema import OverlayPointer
from backend.sim4.integration.export_state import export_state_records, StateSource
from backend.sim4.integration.manifest_schema import (
    ManifestV0_1,
    RecordPointer,
    DiffInventory,
    IntegritySpec,
)
from backend.sim4.integration.kvp_version import KVP_VERSION
from backend.sim4.integration.schema_version import INTEGRATION_SCHEMA_VERSION


class _DummySource(StateSource):
    def get_state(self, tick: int):  # type: ignore[override]
        return {"tick": tick, "value": tick, "pos": {"x": tick + 0.123456, "y": 2.0}}


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


def _build_manifest(start_tick=0, end_tick=3, keyframe_ticks=(0,)) -> ManifestV0_1:
    snaps = {}
    diffs = {}
    integ = {}

    for i, t in enumerate(keyframe_ticks):
        rp = _ptr_snapshot(t)
        snaps[t] = rp
        integ[rp.id] = _sha_like(10 + i)

    for ft in range(start_tick, end_tick):
        rp = _ptr_diff(ft)
        diffs[ft] = rp
        integ[rp.id] = _sha_like(100 + ft)

    # Minimal anchors/spec to satisfy ManifestV0_1
    anchors = __import__("backend.sim4.integration.run_anchors", fromlist=["RunAnchors"]).RunAnchors.from_dict(
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
    render_spec = __import__("backend.sim4.integration.render_spec", fromlist=["RenderSpec"]).RenderSpec.from_dict(
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
    )
    return ManifestV0_1(
        kvp_version=KVP_VERSION,
        schema_version=INTEGRATION_SCHEMA_VERSION,
        run_anchors=anchors,
        render_spec=render_spec,
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


def _read_jsonl_lines(path: Path):
    raw = path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")  # no BOM
    lines = [ln for ln in raw.decode("utf-8").split("\n") if ln.strip()]
    return [json.loads(ln) for ln in lines]


def test_export_ui_events_and_psycho_frames(tmp_path: Path):
    # Prepare synthetic run manifest and state records to ensure separation later
    manifest = _build_manifest(start_tick=0, end_tick=3, keyframe_ticks=(0, 2))
    export_state_records(tmp_path, manifest, _DummySource())

    # Prepare overlay inputs
    events = [
        {"tick": 0, "event_id": "b", "kind": "click", "data": {"x": 1.23456}},
        {"tick": 0, "event_id": "a", "kind": "hover", "data": {"x": 1.23444}},
        {"tick": 2, "event_id": "z", "kind": "note", "data": {}},
    ]
    frames = [
        {"tick": 1, "nodes": [{"id": "n2", "data": {"w": 2.3456}}, {"id": "n1", "data": {"w": 2.3001}}],
         "edges": [{"src_id": "n1", "dst_id": "n2", "kind": "rel", "data": {"p": 0.5004}}]},
        {"tick": 3, "nodes": [{"id": "n3", "data": {}}], "edges": []},
    ]

    ui_rel = export_ui_events_jsonl(tmp_path, start_tick=0, end_tick=3, events=events, batch_span_ticks=2)
    psycho_rel = export_psycho_frames_jsonl(tmp_path, frames)

    # Manifest overlay pointers would reference these relative paths
    op1 = OverlayPointer.from_dict({"rel_path": ui_rel, "format": "JSONL"})
    op2 = OverlayPointer.from_dict({"rel_path": psycho_rel, "format": "JSONL"})
    assert op1.rel_path == "overlays/ui_events.jsonl"
    assert op2.rel_path == "overlays/psycho_frames.jsonl"

    # Read back JSONL and validate envelopes and ordering/quantization
    ui_lines = _read_jsonl_lines(tmp_path / ui_rel)
    assert len(ui_lines) == 2  # batches: [0..1], [2..3]
    for env in ui_lines:
        validate_envelope(env)
        assert envelope_msg_type(env) == "X_UI_EVENT_BATCH"
        p = env["payload"]
        # schema_version enforced
        assert p["schema_version"] == INTEGRATION_SCHEMA_VERSION
        # ordering inside events is canonical (tick,event_id)
        if p["start_tick"] == 0:
            ids = [(e["tick"], e["event_id"]) for e in p["events"]]
            assert ids == [(0, "a"), (0, "b")]  # sorted by event_id within same tick
            # quantization Q1E3 applied
            xs = [e["data"].get("x") for e in p["events"]]
            assert xs == [1.234, 1.235]

    psycho_lines = _read_jsonl_lines(tmp_path / psycho_rel)
    assert len(psycho_lines) == 2
    for env in psycho_lines:
        validate_envelope(env)
        assert envelope_msg_type(env) == "X_PSYCHO_FRAME"
        p = env["payload"]
        assert p["schema_version"] == INTEGRATION_SCHEMA_VERSION
        # nodes sorted by id, edges sorted by tuple
        if p["tick"] == 1:
            node_ids = [n["id"] for n in p["nodes"]]
            assert node_ids == ["n1", "n2"]
            # quantization
            w_vals = [n["data"].get("w") for n in p["nodes"]]
            assert w_vals == [2.3, 2.346]
            assert p["edges"][0]["data"]["p"] == 0.5

    # Guardrail: ensure no REPLAY_ appears in overlay files
    for path in [tmp_path / ui_rel, tmp_path / psycho_rel]:
        txt = path.read_text(encoding="utf-8")
        assert "REPLAY_" not in txt

    # Separation test: snapshot/diff payloads do not contain overlays keys
    snap_path = tmp_path / manifest.snapshots[0].rel_path
    snap = json.loads((snap_path.read_text("utf-8")))
    for k in ("ui_events", "psycho", "overlays"):
        assert k not in snap["payload"]

    # And a diff
    diff_path = tmp_path / manifest.diffs.diffs_by_from_tick[0].rel_path
    diff = json.loads((diff_path.read_text("utf-8")))
    for k in ("ui_events", "psycho", "overlays"):
        assert k not in diff["payload"]


def test_overlay_schema_validation_failures():
    # UIEventBatch bad schema_version
    with pytest.raises(ValueError):
        UIEventBatch.from_dict({
            "schema_version": "999",
            "start_tick": 0,
            "end_tick": 0,
            "events": [],
        })
    # PsychoFrame bad tick
    with pytest.raises(ValueError):
        PsychoFrame.from_dict({
            "schema_version": INTEGRATION_SCHEMA_VERSION,
            "tick": -1,
            "nodes": [],
            "edges": [],
        })
