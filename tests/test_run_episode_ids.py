from __future__ import annotations

import types
from pathlib import Path

import pytest

from loopforge.analytics.reporting import DaySummary, AgentDayStats, summarize_episode, EpisodeSummary
from loopforge.analytics.analysis_api import episode_summary_to_dict


def _mk_day(idx: int, tension: float = 0.0) -> DaySummary:
    stats: dict[str, AgentDayStats] = {}
    return DaySummary(
        day_index=idx,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats=stats,
        total_incidents=0,
        supervisor_activity=0.0,
        beliefs={},
        belief_attributions={},
        reflection_states={},
        emotion_states={},
    )


def test_summarize_episode_sets_ids():
    days = [_mk_day(0, 0.1), _mk_day(1, 0.2)]
    ep: EpisodeSummary = summarize_episode(
        days,
        episode_id="ep-test-123",
        run_id="run-test-abc",
        episode_index=0,
    )
    assert getattr(ep, "episode_id", None) == "ep-test-123"
    assert getattr(ep, "run_id", None) == "run-test-abc"
    assert getattr(ep, "episode_index", None) == 0


def test_episode_summary_to_dict_includes_ids():
    days = [_mk_day(0, 0.1), _mk_day(1, 0.2)]
    ep: EpisodeSummary = summarize_episode(
        days,
        episode_id="ep-test-456",
        run_id="run-test-def",
        episode_index=7,
    )
    out = episode_summary_to_dict(ep)
    assert "run_id" in out and out["run_id"] == "run-test-def"
    assert "episode_id" in out and out["episode_id"] == "ep-test-456"
    assert "episode_index" in out and out["episode_index"] == 7


@pytest.mark.parametrize("days", [0, 1])
def test_cli_view_episode_threads_ids(monkeypatch: pytest.MonkeyPatch, days: int):
    """
    Patch summarize_episode in CLI module to capture the identity kwargs
    passed from view_episode without running the whole pipeline.
    """
    import scripts.run_simulation as cli

    captured = {}

    def fake_summarize(day_summaries, **kwargs):  # signature to accept our new kwargs
        # Store a shallow copy of kwargs for assertions
        captured.update({k: kwargs.get(k) for k in ("run_id", "episode_id", "episode_index")})
        # Return a minimal EpisodeSummary so CLI can continue printing harmlessly
        return summarize_episode(day_summaries, **kwargs)

    monkeypatch.setattr(cli, "summarize_episode", fake_summarize)

    # Also avoid reading actual files by patching compute_day_summary to return empty days
    def fake_compute_day_summary(day_index: int, **_):
        return _mk_day(day_index, tension=0.0)

    monkeypatch.setattr(cli, "compute_day_summary", fake_compute_day_summary)

    # Call the command function directly (Typer app not used here)
    cli.view_episode(
        action_log_path=Path("/nonexistent.jsonl"),
        supervisor_log_path=None,
        steps_per_day=10,
        days=days,
        narrative=False,
        recap=False,
        daily_log=False,
        psych_board=False,
    )

    assert "run_id" in captured and isinstance(captured["run_id"], str) and len(captured["run_id"]) > 0
    assert "episode_id" in captured and isinstance(captured["episode_id"], str) and len(captured["episode_id"]) > 0
    assert captured.get("episode_index") == 0
