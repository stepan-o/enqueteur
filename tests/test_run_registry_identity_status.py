from __future__ import annotations

import json
from pathlib import Path

from loopforge.analytics.run_registry import (
    EpisodeRecord,
    append_episode_record,
    load_registry,
    registry_path,
)


def test_episode_record_round_trip_with_status_and_source(tmp_path):
    base = tmp_path
    rec = EpisodeRecord(
        run_id="run-1",
        episode_id="ep-1",
        episode_index=0,
        created_at="2025-01-01T00:00:00+00:00",
        steps_per_day=20,
        days=3,
        status="resolved",
        source="simulation",
    )
    append_episode_record(rec, base_dir=base)

    rows = load_registry(base_dir=base)
    assert len(rows) == 1
    got = rows[0]
    assert got.run_id == rec.run_id
    assert got.episode_id == rec.episode_id
    assert got.episode_index == rec.episode_index
    assert got.status == "resolved"
    assert got.source == "simulation"


def test_load_registry_backward_compat_without_status_source(tmp_path):
    base = tmp_path
    path = registry_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write a legacy line without status/source fields
    legacy = {
        "run_id": "run-legacy",
        "episode_id": "ep-legacy",
        "episode_index": 1,
        "created_at": "2024-12-31T23:59:59+00:00",
        "steps_per_day": 10,
        "days": 1,
    }
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(legacy) + "\n")

    rows = load_registry(base_dir=base)
    assert len(rows) == 1
    rec = rows[0]
    assert rec.run_id == "run-legacy"
    assert rec.episode_id == "ep-legacy"
    assert rec.status is None
    assert rec.source is None
