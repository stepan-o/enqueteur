from __future__ import annotations

import json
from pathlib import Path

from loopforge.analytics.identity_helpers import (
    detect_latest_episode_identity,
    verify_episode_identity_in_log,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r))
            f.write("\n")


def test_detect_latest_episode_identity_missing_file(tmp_path):
    p = tmp_path / "no_such.log"
    assert detect_latest_episode_identity(p) is None


def test_detect_latest_episode_identity_empty_file(tmp_path):
    p = tmp_path / "actions.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n")
    assert detect_latest_episode_identity(p) is None


def test_detect_latest_episode_identity_single_identity(tmp_path):
    p = tmp_path / "actions.jsonl"
    rows = [
        {"run_id": "run-A", "episode_id": "ep-A", "episode_index": 0, "step": 1},
        {"run_id": "run-A", "episode_id": "ep-A", "episode_index": 0, "step": 2},
    ]
    _write_jsonl(p, rows)
    assert detect_latest_episode_identity(p) == ("run-A", "ep-A", 0)


def test_detect_latest_episode_identity_multiple_identities_latest_wins(tmp_path):
    p = tmp_path / "actions.jsonl"
    rows = [
        {"run_id": "run-A", "episode_id": "ep-A", "episode_index": 0, "step": 1},
        {"garbage": True},
        {"run_id": "run-B", "episode_id": "ep-B", "episode_index": 2, "step": 1},
        {"run_id": "run-B", "episode_id": "ep-B", "episode_index": 2, "step": 2},
    ]
    _write_jsonl(p, rows)
    assert detect_latest_episode_identity(p) == ("run-B", "ep-B", 2)


def test_detect_latest_episode_identity_malformed_lines_are_skipped(tmp_path):
    p = tmp_path / "actions.jsonl"
    # Include malformed JSON and lines missing identity
    with p.open("w", encoding="utf-8") as f:
        f.write("{not-json}\n")
        f.write(json.dumps({"step": 1}))
        f.write("\n")
        f.write(json.dumps({"run_id": "r1", "episode_id": "e1", "episode_index": 0}))
        f.write("\n")
    assert detect_latest_episode_identity(p) == ("r1", "e1", 0)


def test_verify_episode_identity_in_log_missing_file(tmp_path):
    p = tmp_path / "missing.jsonl"
    assert verify_episode_identity_in_log(p, "r", "e", 0) is False


def test_verify_episode_identity_in_log_exact_match(tmp_path):
    p = tmp_path / "actions.jsonl"
    rows = [
        {"run_id": "r0", "episode_id": "e0", "episode_index": 0},
        {"run_id": "r1", "episode_id": "e1", "episode_index": 1},
    ]
    _write_jsonl(p, rows)
    assert verify_episode_identity_in_log(p, "r1", "e1", 1) is True
    assert verify_episode_identity_in_log(p, "r1", "eX", 1) is False


def test_verify_episode_identity_in_log_malformed_lines(tmp_path):
    p = tmp_path / "actions.jsonl"
    with p.open("w", encoding="utf-8") as f:
        f.write("{oops}\n")
        f.write(json.dumps({"run_id": "r1", "episode_id": "e1", "episode_index": 1}))
        f.write("\n")
    assert verify_episode_identity_in_log(p, "r1", "e1", 1) is True
