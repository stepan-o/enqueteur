from __future__ import annotations

import json
from pathlib import Path
from typing import List

from loopforge.analytics.run_registry import (
    EpisodeRecord,
    append_episode_record,
    load_registry,
    registry_path,
    utc_now_iso,
)


def test_append_and_load_registry_roundtrip(tmp_path: Path):
    base = tmp_path
    rec = EpisodeRecord(
        run_id="run-abc",
        episode_id="ep-xyz",
        episode_index=0,
        created_at=utc_now_iso(),
        steps_per_day=20,
        days=3,
    )
    append_episode_record(rec, base_dir=base)

    rows: List[EpisodeRecord] = load_registry(base_dir=base)
    assert len(rows) == 1
    r = rows[0]
    assert r.run_id == rec.run_id
    assert r.episode_id == rec.episode_id
    assert r.episode_index == rec.episode_index
    assert r.steps_per_day == rec.steps_per_day
    assert r.days == rec.days
    assert isinstance(r.created_at, str) and len(r.created_at) >= 10


def test_registry_handles_multiple_records_and_malformed_lines(tmp_path: Path):
    # Manually compose a registry file with valid, malformed, valid lines
    path = registry_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    valid1 = EpisodeRecord(
        run_id="run-1",
        episode_id="ep-1",
        episode_index=0,
        created_at="2025-01-01T00:00:00+00:00",
        steps_per_day=10,
        days=2,
    ).to_dict()
    malformed = "{this is not valid json}"
    valid2 = EpisodeRecord(
        run_id="run-2",
        episode_id="ep-2",
        episode_index=1,
        created_at="2025-01-02T00:00:00+00:00",
        steps_per_day=50,
        days=5,
    ).to_dict()

    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(valid1) + "\n")
        f.write(malformed + "\n")
        f.write(json.dumps(valid2) + "\n")

    rows = load_registry(base_dir=tmp_path)
    assert len(rows) == 2
    assert rows[0].run_id == "run-1"
    assert rows[1].run_id == "run-2"


def test_list_runs_cli_prints_something(tmp_path: Path, capsys):
    # Seed a registry with two records in tmp_path
    base = tmp_path
    rec1 = EpisodeRecord(
        run_id="seed-run-1",
        episode_id="seed-ep-1",
        episode_index=0,
        created_at="2025-11-16T12:00:00+00:00",
        steps_per_day=20,
        days=3,
    )
    rec2 = EpisodeRecord(
        run_id="seed-run-2",
        episode_id="seed-ep-2",
        episode_index=0,
        created_at="2025-11-16T13:00:00+00:00",
        steps_per_day=50,
        days=5,
    )
    append_episode_record(rec1, base_dir=base)
    append_episode_record(rec2, base_dir=base)

    # Invoke the CLI command function directly with a base override
    from loopforge.cli import sim_cli as cli

    # Call with limit=1 to only print the most recent of the two records
    cli.list_runs(limit=1, registry_base=base)

    out = capsys.readouterr().out
    assert "RUN HISTORY" in out
    # The most recent (rec2) should appear due to limit=1
    assert "seed-run-2" in out
    # And the line should include the expected fields
    assert "episode_id=seed-ep-2" in out and "idx=0" in out and "steps_per_day=50" in out
