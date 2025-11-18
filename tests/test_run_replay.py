from __future__ import annotations

import json
from pathlib import Path

from loopforge.analysis_api import analyze_episode_from_record
from loopforge.run_registry import EpisodeRecord, append_episode_record, registry_path


RUN_ID = "r2-run"
EPISODE_ID = "r2-ep"
EPISODE_INDEX = 0


def _mk_action(step: int, name: str, role: str, mode: str, *, run_id: str, episode_id: str) -> dict:
    return {
        "step": int(step),
        "agent_name": name,
        "role": role,
        "mode": mode,
        "intent": "work" if mode == "guardrail" else "inspect",
        "move_to": None,
        "targets": [],
        "riskiness": 0.0,
        "narrative": "",
        "outcome": None,
        "raw_action": {},
        "perception": {"emotions": {"stress": 0.1}, "perception_mode": "accurate"},
        "policy_name": None,
        "episode_index": EPISODE_INDEX,
        "day_index": step // 10,
        "run_id": run_id,
        "episode_id": episode_id,
    }


def test_analyze_episode_from_record_round_trip(tmp_path: Path):
    # Write a tiny action log for one episode (one day of 10 steps)
    actions_path = tmp_path / "actions.jsonl"
    lines = [json.dumps(_mk_action(i, "Delta", "qa", "guardrail", run_id=RUN_ID, episode_id=EPISODE_ID)) for i in range(10)]
    actions_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Build a matching EpisodeRecord and analyze
    rec = EpisodeRecord(
        run_id=RUN_ID,
        episode_id=EPISODE_ID,
        episode_index=EPISODE_INDEX,
        created_at="2025-01-01T00:00:00+00:00",
        steps_per_day=10,
        days=1,
    )

    ep = analyze_episode_from_record(rec, action_log_path=actions_path, supervisor_log_path=None)

    from loopforge.reporting import EpisodeSummary
    assert isinstance(ep, EpisodeSummary)
    assert getattr(ep, "run_id", None) == RUN_ID
    assert getattr(ep, "episode_id", None) == EPISODE_ID
    assert getattr(ep, "episode_index", None) == EPISODE_INDEX
    assert len(ep.days) == 1


def test_replay_latest_uses_registry(tmp_path: Path, capsys):
    # Prepare logs and registry
    actions_path = tmp_path / "actions.jsonl"
    # Two agents over 10 steps day 0
    lines = []
    for i in range(10):
        lines.append(json.dumps(_mk_action(i, "Delta", "maintenance", "guardrail", run_id=RUN_ID, episode_id=EPISODE_ID)))
        lines.append(json.dumps(_mk_action(i, "Nova", "qa", "context", run_id=RUN_ID, episode_id=EPISODE_ID)))
    actions_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Append registry record under tmp registry base
    rec = EpisodeRecord(
        run_id=RUN_ID,
        episode_id=EPISODE_ID,
        episode_index=EPISODE_INDEX,
        created_at="2025-01-01T00:00:00+00:00",
        steps_per_day=10,
        days=1,
    )
    append_episode_record(rec, base_dir=tmp_path)

    # Invoke CLI function directly (like other tests)
    import scripts.run_simulation as cli

    cli.replay_episode(
        run_id=None,
        episode_index=0,
        latest=True,
        recap=True,
        action_log_path=actions_path,
        supervisor_log_path=None,
        registry_base=tmp_path,
    )

    out = capsys.readouterr().out
    assert "EPISODE RECAP" in out
    assert "RUN HISTORY" not in out


def test_replay_missing_run_id_errors(tmp_path: Path, capsys):
    # No registry rows; calling without --latest and without --run-id should error
    import scripts.run_simulation as cli

    try:
        cli.replay_episode(
            run_id=None,
            episode_index=0,
            latest=False,
            recap=False,
            action_log_path=tmp_path / "actions.jsonl",
            supervisor_log_path=None,
            registry_base=tmp_path,
        )
    except SystemExit:
        # Typer.Exit triggers SystemExit when called directly
        pass

    out = capsys.readouterr().out
    assert "Missing required --run-id" in out
