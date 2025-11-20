from __future__ import annotations

from pathlib import Path

import json
import typer
from typer.testing import CliRunner

from scripts.run_simulation import app
from loopforge.analytics.run_registry import EpisodeRecord, append_episode_record, registry_path

runner = CliRunner()


def _write_action_entry(path: Path, **overrides):
    base = {
        "step": 0,
        "agent_name": "Sprocket",
        "role": "maintenance",
        "mode": "guardrail",
        "intent": "work",
        "move_to": "factory_floor",
        "targets": [],
        "riskiness": 0.1,
        "narrative": "Routine maintenance",
        "outcome": None,
        "raw_action": {"action_type": "work", "destination": "factory_floor"},
        "perception": {"emotions": {"stress": 0.2, "curiosity": 0.5, "satisfaction": 0.5}},
        "policy_name": None,
        "episode_index": 0,
        "day_index": 0,
        "run_id": "run-x",
        "episode_id": "ep-x",
    }
    base.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(base))
        f.write("\n")


def test_view_day_latest_happy_path(tmp_path: Path):
    reg_base = tmp_path
    reg_file = registry_path(reg_base)
    # Older record
    append_episode_record(
        EpisodeRecord(
            run_id="run-old", episode_id="ep-old", episode_index=0, created_at="2025-01-01T00:00:00Z", steps_per_day=50, days=1
        ),
        base_dir=reg_base,
    )
    # Latest record with days=1
    append_episode_record(
        EpisodeRecord(
            run_id="run-latest", episode_id="ep-latest", episode_index=0, created_at="2025-01-02T00:00:00Z", steps_per_day=50, days=1
        ),
        base_dir=reg_base,
    )

    # Action log containing at least one entry for latest run/episode
    act_log = tmp_path / "actions.jsonl"
    _write_action_entry(act_log, step=0, run_id="run-latest", episode_id="ep-latest")

    result = runner.invoke(
        app,
        [
            "view-day",
            "--latest",
            "--action-log-path",
            str(act_log),
            "--registry-base",
            str(reg_base),
        ],
    )
    assert result.exit_code == 0, result.output
    # Should mention Day 0 — Summary
    assert "Day 0 — Summary" in result.output

    # Also works when day index is explicitly provided as positional
    result2 = runner.invoke(
        app,
        [
            "view-day",
            "--latest",
            "0",
            "--action-log-path",
            str(act_log),
            "--registry-base",
            str(reg_base),
        ],
    )
    assert result2.exit_code == 0, result2.output
    assert "Day 0 — Summary" in result2.output


def test_view_day_latest_days_zero(tmp_path: Path):
    reg_base = tmp_path
    append_episode_record(
        EpisodeRecord(
            run_id="run-zero", episode_id="ep-zero", episode_index=0, created_at="2025-01-03T00:00:00Z", steps_per_day=50, days=0
        ),
        base_dir=reg_base,
    )

    act_log = tmp_path / "actions.jsonl"  # may be empty; CLI should error before reading

    result = runner.invoke(
        app,
        [
            "view-day",
            "--latest",
            "--action-log-path",
            str(act_log),
            "--registry-base",
            str(reg_base),
        ],
    )
    assert result.exit_code != 0
    assert "0 full days" in result.output or "0 full days" in (result.stderr or "")


def test_view_day_latest_mixing_ids_rejected(tmp_path: Path):
    reg_base = tmp_path
    # Put a minimal record so latest would otherwise work
    append_episode_record(
        EpisodeRecord(
            run_id="run-a", episode_id="ep-a", episode_index=0, created_at="2025-01-02T00:00:00Z", steps_per_day=50, days=1
        ),
        base_dir=reg_base,
    )
    act_log = tmp_path / "actions.jsonl"

    result = runner.invoke(
        app,
        [
            "view-day",
            "--latest",
            "some_run",
            "some_ep",
            "0",
            "--action-log-path",
            str(act_log),
            "--registry-base",
            str(reg_base),
        ],
    )
    assert result.exit_code != 0
    assert "Do not provide RUN_ID/EPISODE_ID" in result.output


def test_view_day_legacy_explicit_mode(tmp_path: Path):
    # Create explicit run/episode and a matching action log entry
    run_id = "run-explicit"
    episode_id = "ep-explicit"
    act_log = tmp_path / "actions.jsonl"
    _write_action_entry(act_log, step=0, run_id=run_id, episode_id=episode_id)

    result = runner.invoke(
        app,
        [
            "view-day",
            run_id,
            episode_id,
            "0",
            "--action-log-path",
            str(act_log),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Day 0 — Summary" in result.output
