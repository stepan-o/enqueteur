from __future__ import annotations

import sys
import types
from pathlib import Path


def make_dummy_snapshot(tick_index: int, time_seconds: float, episode_id: int | None):
    class Dummy:
        __slots__ = ("tick_index", "time_seconds", "episode_id", "rooms", "agents", "items")

        def __init__(self):
            self.tick_index = tick_index
            self.time_seconds = time_seconds
            self.episode_id = episode_id
            self.rooms = []
            self.agents = []
            self.items = []

    return Dummy()


def test_exporter_writes_layout_and_manifest(tmp_path: Path):
    # Local imports to avoid polluting sys.modules for decoupling checks
    from backend.sim4.integration.schema import IntegrationSchemaVersion, RunManifest
    from backend.sim4.integration.frame_builder import build_tick_frame
    from backend.sim4.integration.exporter import export_run

    # Build two frames deterministically
    snap1 = make_dummy_snapshot(1, 0.1, 9)
    snap2 = make_dummy_snapshot(2, 0.2, 9)
    f1 = build_tick_frame(snap1, events=())
    f2 = build_tick_frame(snap2, events=())

    # Seed manifest (values will be finalized by exporter)
    seed_manifest = RunManifest(
        schema_version=IntegrationSchemaVersion(1, 0, 0),
        run_id=111,
        world_id=5,
        episode_id=9,
        tick_start=0,
        tick_end=0,
        frame_count=0,
        time_start_seconds=None,
        time_end_seconds=None,
        artifacts={},
        exported_at_utc_ms=None,
    )

    out_dir = tmp_path / "export_a"
    finalized = export_run(out_dir, manifest=seed_manifest, frames=[f1, f2])

    # Directory layout
    manifest_path = out_dir / "manifest.json"
    frames_path = out_dir / "frames" / "frames.jsonl"
    assert manifest_path.is_file(), "manifest.json missing"
    assert frames_path.is_file(), "frames/frames.jsonl missing"

    # Manifest correctness
    assert finalized.tick_start == 1
    assert finalized.tick_end == 2
    assert finalized.frame_count == 2
    assert finalized.artifacts.get("manifest") == "manifest.json"
    assert finalized.artifacts.get("frames") == "frames/frames.jsonl"
    # events not present because we did not supply any
    assert "events" not in finalized.artifacts


def test_exporter_is_deterministic_byte_identical(tmp_path: Path):
    from backend.sim4.integration.schema import IntegrationSchemaVersion, RunManifest
    from backend.sim4.integration.frame_builder import build_tick_frame
    from backend.sim4.integration.exporter import export_run

    snap1 = make_dummy_snapshot(3, 0.3, 7)
    snap2 = make_dummy_snapshot(4, 0.4, 7)
    f1 = build_tick_frame(snap1, events=())
    f2 = build_tick_frame(snap2, events=())

    seed_manifest = RunManifest(
        schema_version=IntegrationSchemaVersion(1, 0, 0),
        run_id=222,
        world_id=8,
        episode_id=7,
        tick_start=0,
        tick_end=0,
        frame_count=0,
        time_start_seconds=None,
        time_end_seconds=None,
        artifacts={},
        exported_at_utc_ms=1234567890,  # injected, constant
    )

    # First export
    out_a = tmp_path / "a"
    export_run(out_a, manifest=seed_manifest, frames=[f1, f2])
    # Second export with identical inputs
    out_b = tmp_path / "b"
    export_run(out_b, manifest=seed_manifest, frames=[f1, f2])

    def read_bytes(path: Path) -> bytes:
        return path.read_bytes()

    # Compare manifest.json
    assert read_bytes(out_a / "manifest.json") == read_bytes(out_b / "manifest.json")
    # Compare frames.jsonl
    assert read_bytes(out_a / "frames" / "frames.jsonl") == read_bytes(out_b / "frames" / "frames.jsonl")


def test_importing_exporter_does_not_pull_engine_modules():
    # Ensure engine modules are not already loaded
    engine_modules = [
        "backend.sim4.runtime",
        "backend.sim4.world",
        "backend.sim4.snapshot",
        "backend.sim4.narrative",
    ]
    for m in engine_modules:
        sys.modules.pop(m, None)

    import importlib

    importlib.invalidate_caches()
    pkg = importlib.import_module("backend.sim4.integration.exporter")
    assert isinstance(pkg, types.ModuleType)
    for m in engine_modules:
        assert m not in sys.modules, f"Module {m} imported implicitly by exporter"
