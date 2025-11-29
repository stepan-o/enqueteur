from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopforge.cli.sim_cli import view_episode


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r))
            f.write("\n")


def test_view_episode_latest_happy_path_appends_verified_registry(tmp_path, monkeypatch, capsys):
    # Seed action log with a consistent identity
    actions = tmp_path / "logs" / "loopforge_actions.jsonl"
    rows = [
        {"run_id": "run-A", "episode_id": "ep-A", "episode_index": 0, "step": 1},
        {"run_id": "run-A", "episode_id": "ep-A", "episode_index": 0, "step": 2},
    ]
    _write_jsonl(actions, rows)

    # Capture appended record without touching filesystem registry
    appended = {}

    import loopforge.analytics.run_registry as rr

    def fake_append(rec, base_dir=None):
        appended["rec"] = rec

    monkeypatch.setattr(rr, "append_episode_record", fake_append)

    # Execute: No explicit IDs passed; detection must use logs and append
    view_episode(None, None, action_log_path=actions, steps_per_day=50, days=3, latest=False)

    # Assert registry append happened with matching IDs and resolved status
    assert "rec" in appended, "Expected append_episode_record to be called"
    rec = appended["rec"]
    assert rec.run_id == "run-A"
    assert rec.episode_id == "ep-A"
    assert rec.episode_index == 0
    # Optional new fields from Sprint 1 should be populated per Sprint 2 behavior
    assert getattr(rec, "status", None) == "resolved"
    assert getattr(rec, "source", None) == "cli-view-episode"


def test_view_episode_no_identity_in_logs_skips_registry(tmp_path, monkeypatch, capsys):
    # Empty action log → detection returns None
    actions = tmp_path / "logs" / "loopforge_actions.jsonl"
    actions.parent.mkdir(parents=True, exist_ok=True)
    actions.write_text("\n")

    called = {"append": False}

    import loopforge.analytics.run_registry as rr

    def fake_append(*args, **kwargs):
        called["append"] = True

    monkeypatch.setattr(rr, "append_episode_record", fake_append)

    # Run: should print a clear message and not append
    view_episode(None, None, action_log_path=actions, steps_per_day=50, days=3, latest=False)
    out = capsys.readouterr()
    assert "no registry entry was written" in out.err.lower()
    assert called["append"] is False


def test_view_episode_explicit_ids_not_in_logs_skips_registry(tmp_path, monkeypatch, capsys):
    # Seed action log with identity X
    actions = tmp_path / "logs" / "loopforge_actions.jsonl"
    rows = [
        {"run_id": "run-A", "episode_id": "ep-A", "episode_index": 0, "step": 1},
    ]
    _write_jsonl(actions, rows)

    called = {"append": False}

    import loopforge.analytics.run_registry as rr

    def fake_append(*args, **kwargs):
        called["append"] = True

    monkeypatch.setattr(rr, "append_episode_record", fake_append)

    # Provide explicit non-matching IDs → verify should fail → skip append
    view_episode("run-B", "ep-B", action_log_path=actions, steps_per_day=50, days=3, latest=False)
    out = capsys.readouterr()
    assert "registry entry not written" in out.err.lower()
    assert called["append"] is False
