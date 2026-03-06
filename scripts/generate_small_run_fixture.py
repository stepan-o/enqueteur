from __future__ import annotations

"""
ARTIFACTS ONLY — NO REPLAY_ — NO LIVE SESSION*

One-shot generator for the S14.8 golden export fixture.

This script produces a tiny, deterministic run under:
  fixtures/kvp/v0_1/small_run/

It uses the real exporter code paths (export_state + export_overlays) and then
computes SHA-256 for all committed files to write fixture_hashes.json.

Safe to run multiple times; output is deterministic and idempotent.
"""

import json
import uuid
from pathlib import Path
from typing import Dict
from hashlib import sha256
import sys

# Ensure repository root is on sys.path so `backend` package imports work when run directly
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.sim4.integration.kvp_version import KVP_VERSION
from backend.sim4.integration.schema_version import INTEGRATION_SCHEMA_VERSION
from backend.sim4.integration.manifest_schema import (
    ManifestV0_1,
    RecordPointer,
    DiffInventory,
    IntegritySpec,
    OverlayPointer,
    LayoutHints,
)
from backend.sim4.integration.export_state import StateSource, export_state_records
from backend.sim4.integration.export_overlays import (
    export_ui_events_jsonl,
    export_psycho_frames_jsonl,
)
from backend.sim4.integration.manifest_writer import write_manifest


RUN_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "kvp" / "v0_1" / "small_run"


class _DummySource(StateSource):
    def get_state(self, tick: int):  # type: ignore[override]
        return {
            "world": {
                "world_output": float(tick) + 0.123456,
                "day_index": 1,
                "ticks_per_day": 60,
                "tick_in_day": tick,
                "time_of_day": float(tick) / 60.0,
                "day_phase": "day",
                "phase_progress": float(tick) / 60.0,
            },
            "rooms": [
                {
                    "room_id": 2,
                    "label": "B",
                    "kind_code": 0,
                    "occupants": [],
                    "items": [],
                    "neighbors": [1],
                    "tension_tier": "low",
                    "highlight": False,
                },
                {
                    "room_id": 1,
                    "label": "A",
                    "kind_code": 0,
                    "occupants": [],
                    "items": [],
                    "neighbors": [2],
                    "tension_tier": "low",
                    "highlight": False,
                },
            ],
            "agents": [],
            "items": [],
            "objects": [],
            "events": [],
        }


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


def _anchors_dict() -> Dict[str, object]:
    return {
        "engine_name": "EnqueteurSim",
        "engine_version": "1.0.0",
        "schema_version": INTEGRATION_SCHEMA_VERSION,
        "world_id": str(uuid.UUID("00000000-0000-4000-8000-000000000001")),
        "run_id": str(uuid.UUID("00000000-0000-4000-8000-000000000002")),
        "seed": 1,
        "tick_rate_hz": 30,
        "time_origin_ms": 0,
    }


def _render_spec_dict() -> Dict[str, object]:
    return {
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


def _sha256_hex(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = RUN_ROOT
    root.mkdir(parents=True, exist_ok=True)

    start_tick = 0
    end_tick = 3
    keyframe_ticks = [0, 2]

    # Build pointers
    snaps = {t: _ptr_snapshot(t) for t in keyframe_ticks}
    diffs = {ft: _ptr_diff(ft) for ft in range(start_tick, end_tick)}

    # Export records
    source = _DummySource()
    # Build a temporary manifest-like object to pass the pointers into exporter
    from backend.sim4.integration.manifest_schema import (
        ManifestV0_1 as _MV,
        DiffInventory as _DI,
        IntegritySpec as _IS,
    )
    temp_manifest = _MV(
        kvp_version=KVP_VERSION,
        schema_version=INTEGRATION_SCHEMA_VERSION,
        run_anchors=__import__(
            "backend.sim4.integration.run_anchors", fromlist=["RunAnchors"]
        ).RunAnchors.from_dict(_anchors_dict()),
        render_spec=__import__(
            "backend.sim4.integration.render_spec", fromlist=["RenderSpec"]
        ).RenderSpec.from_dict(_render_spec_dict()),
        available_start_tick=start_tick,
        available_end_tick=end_tick,
        channels=["WORLD"],
        keyframe_interval=None,
        keyframe_ticks=list(keyframe_ticks),
        snapshots=snaps,
        diffs=_DI(diffs_by_from_tick=diffs),
        integrity=_IS.from_dict({"hash_alg": "SHA-256", "records_sha256": {"placeholder": "0" * 64}}),
        layout=LayoutHints(records_root=".", snapshots_dir="state/snapshots", diffs_dir="state/diffs", overlays_dir="overlays", diff_storage="PER_TICK_FILES"),
        overlays={},
    )
    # Export state records
    export_state_records(root, temp_manifest, source)

    # Export overlays
    events = [
        {"tick": 0, "event_id": "a", "kind": "hover", "data": {"x": 1.23444}},
        {"tick": 0, "event_id": "b", "kind": "click", "data": {"x": 1.23456}},
        {"tick": 2, "event_id": "z", "kind": "note", "data": {}},
    ]
    ui_rel = export_ui_events_jsonl(root, start_tick=0, end_tick=3, events=events, batch_span_ticks=2)
    psycho_rel = export_psycho_frames_jsonl(
        root,
        frames=[
            {"tick": 1, "nodes": [{"id": "n2", "data": {"w": 2.3456}}, {"id": "n1", "data": {"w": 2.3001}}], "edges": [{"src_id": "n1", "dst_id": "n2", "kind": "rel", "data": {"p": 0.5004}}]},
            {"tick": 3, "nodes": [{"id": "n3", "data": {}}], "edges": []},
        ],
    )

    # Compute integrity over records (by pointer id)
    integ_map: Dict[str, str] = {}
    for t, rp in snaps.items():
        integ_map[rp.id] = _sha256_hex(root / rp.rel_path)
    for ft, rp in diffs.items():
        integ_map[rp.id] = _sha256_hex(root / rp.rel_path)

    integrity = IntegritySpec.from_dict({"hash_alg": "SHA-256", "records_sha256": integ_map})

    # Build final manifest with overlays and layout hints
    mv = ManifestV0_1.from_dict(
        {
            "kvp_version": KVP_VERSION,
            "schema_version": INTEGRATION_SCHEMA_VERSION,
            "run_anchors": _anchors_dict(),
            "render_spec": _render_spec_dict(),
            "available_start_tick": start_tick,
            "available_end_tick": end_tick,
            "channels": ["WORLD"],
            "keyframe_ticks": keyframe_ticks,
            "snapshots": {str(k): v.to_dict() for k, v in snaps.items()},
            "diffs": DiffInventory(diffs_by_from_tick=diffs).to_dict(),
            "integrity": integrity.to_dict(),
            "layout": LayoutHints(records_root=".", snapshots_dir="state/snapshots", diffs_dir="state/diffs", overlays_dir="overlays", diff_storage="PER_TICK_FILES").to_dict(),
            "overlays": {
                "X_UI_EVENT_BATCH": OverlayPointer(rel_path=ui_rel, format="JSONL").to_dict(),
                "X_PSYCHO_FRAME": OverlayPointer(rel_path=psycho_rel, format="JSONL").to_dict(),
            },
        }
    )

    # Write manifest
    write_manifest(root / "manifest.kvp.json", mv)

    # Build fixture hashes over files that must be byte-stable
    files = [
        Path("manifest.kvp.json"),
        Path(ui_rel),
        Path(psycho_rel),
    ]
    files += [Path(snaps[t].rel_path) for t in sorted(snaps.keys())]
    files += [Path(diffs[ft].rel_path) for ft in sorted(diffs.keys())]

    mapping: Dict[str, str] = {}
    for rel in files:
        mapping[str(rel)] = _sha256_hex(root / rel)

    (root / "fixture_hashes.json").write_text(json.dumps(mapping, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
