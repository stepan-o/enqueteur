from __future__ import annotations

from pathlib import Path

import json
from typer.testing import CliRunner

from scripts.run_simulation import app
from loopforge.run_registry import EpisodeRecord

runner = CliRunner()


def _write_registry_lines(path: Path, records: list[EpisodeRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_dict()))
            f.write("\n")


def test_view_episode_latest_happy_path(tmp_path, monkeypatch):
    # Point the registry to a temp file
    reg_file = tmp_path / "loopforge_run_registry.jsonl"
    monkeypatch.setattr(
        "loopforge.run_registry.registry_path", lambda base_dir=None: reg_file, raising=True
    )

    # Write two records, the last one is the latest
    older = EpisodeRecord(
        run_id="run-old", episode_id="ep-old", episode_index=0,
        created_at="2025-01-01T00:00:00Z", steps_per_day=50, days=1,
    )
    latest = EpisodeRecord(
        run_id="run-new", episode_id="ep-new", episode_index=0,
        created_at="2025-01-02T00:00:00Z", steps_per_day=50, days=1,
    )
    _write_registry_lines(reg_file, [older, latest])

    # Invoke CLI with --latest; should resolve IDs from registry and succeed
    result = runner.invoke(app, ["view-episode", "--latest"])
    assert result.exit_code == 0, result.output
    # Should print episode summary header
    assert "EPISODE SUMMARY" in result.output

    # With --recap flag, expect recap header
    result2 = runner.invoke(app, ["view-episode", "--latest", "--recap"])
    assert result2.exit_code == 0, result2.output
    assert "EPISODE RECAP" in result2.output


def test_view_episode_latest_no_episodes(tmp_path, monkeypatch):
    # Empty registry file
    reg_file = tmp_path / "loopforge_run_registry.jsonl"
    reg_file.parent.mkdir(parents=True, exist_ok=True)
    reg_file.write_text("")
    monkeypatch.setattr(
        "loopforge.run_registry.registry_path", lambda base_dir=None: reg_file, raising=True
    )

    result = runner.invoke(app, ["view-episode", "--latest"])
    assert result.exit_code != 0
    assert "No episodes found in the registry yet." in (result.output or "") or \
           "No episodes found in the registry yet." in (result.stderr or "")


def test_view_episode_latest_mixing_ids_error(tmp_path, monkeypatch):
    # Minimal registry so latest would otherwise work
    reg_file = tmp_path / "loopforge_run_registry.jsonl"
    monkeypatch.setattr(
        "loopforge.run_registry.registry_path", lambda base_dir=None: reg_file, raising=True
    )
    only = EpisodeRecord(
        run_id="run-x", episode_id="ep-x", episode_index=0,
        created_at="2025-01-01T00:00:00Z", steps_per_day=50, days=1,
    )
    _write_registry_lines(reg_file, [only])

    # Mix explicit IDs with --latest → usage error
    result = runner.invoke(app, ["view-episode", "--latest", "some_run", "some_ep"])
    assert result.exit_code != 0
    assert "Do not provide RUN_ID/EPISODE_ID" in result.output


def test_view_episode_explicit_mode_regression(tmp_path, monkeypatch):
    # Explicit mode should still work without consulting the registry
    # Provide dummy IDs and expect the command to run and print a summary.
    result = runner.invoke(app, ["view-episode", "RUN123", "EP456"])  # defaults for other flags
    assert result.exit_code == 0, result.output
    assert "EPISODE SUMMARY" in result.output
