from __future__ import annotations

from loopforge.analytics.reporting import DaySummary, AgentDayStats, summarize_episode, EpisodeSummary
from loopforge.analytics.analysis_api import episode_summary_to_dict


def _mk_day(idx: int, tension: float = 0.0) -> DaySummary:
    # Minimal DaySummary similar to existing recap tests
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


def test_episode_summary_has_episode_id():
    days = [_mk_day(0, tension=0.1), _mk_day(1, tension=0.2)]
    ep: EpisodeSummary = summarize_episode(days, episode_id="test-123")
    assert getattr(ep, "episode_id", None) == "test-123"


def test_episode_summary_to_dict_includes_episode_id():
    days = [_mk_day(0, tension=0.1), _mk_day(1, tension=0.2)]
    ep: EpisodeSummary = summarize_episode(days, episode_id="test-123")
    out = episode_summary_to_dict(ep)
    assert "episode_id" in out
    assert out["episode_id"] == "test-123"
