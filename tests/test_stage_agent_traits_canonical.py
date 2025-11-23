from __future__ import annotations

from types import SimpleNamespace

from loopforge.stage.stage_episode import StageAgentTraits
from loopforge.stage import build_stage_episode
from loopforge.analytics.reporting import DaySummary, EpisodeSummary, AgentDayStats, AgentEpisodeStats


def test_stage_agent_traits_happy_path_complete_snapshot():
    snapshot = {
        "resilience": 0.8,
        "caution": 0.6,
        "agency": 0.7,
        "trust_supervisor": 0.9,
        "variance": 0.4,
    }
    t = StageAgentTraits(**snapshot)
    assert t.resilience == 0.8
    assert t.caution == 0.6
    assert t.agency == 0.7
    assert t.trust_supervisor == 0.9
    assert t.variance == 0.4
    assert t.to_dict() == snapshot


def test_stage_agent_traits_missing_keys_allowed():
    snapshot = {"resilience": 0.5}
    t = StageAgentTraits(**snapshot)
    d = t.to_dict()
    assert d == {"resilience": 0.5}
    # Others remain None on the dataclass
    assert t.caution is None and t.agency is None and t.trust_supervisor is None and t.variance is None


def _make_min_episode(trait_snapshot_alpha: dict | None):
    agent_stats = {
        "Alpha": AgentDayStats(name="Alpha", role="scout", guardrail_count=1, context_count=2, avg_stress=0.3),
    }
    day0 = DaySummary(day_index=0, perception_mode="accurate", tension_score=0.2, agent_stats=agent_stats, total_incidents=0, supervisor_activity=0.0)
    agents = {
        "Alpha": AgentEpisodeStats(
            name="Alpha",
            role="scout",
            guardrail_total=2,
            context_total=3,
            trait_deltas={},
            stress_start=0.2,
            stress_end=0.3,
            representative_reflection=None,
            visual="",
            vibe="",
            tagline="",
            trait_snapshot=trait_snapshot_alpha,
        )
    }
    return EpisodeSummary(days=[day0], agents=agents, tension_trend=[0.2], episode_id="ep-X", run_id="run-X", episode_index=0)


def test_stage_builder_extra_keys_ignored_and_canonical_only():
    raw = {
        "resilience": 0.9,
        "caution": 0.1,
        "random_extra": 123,
    }
    ep = _make_min_episode(raw)
    stage_ep = build_stage_episode(ep, ep.days, story_arc=None, long_memory=None, character_defs=None, include_narrative=False)
    # Extract serialized agent summary
    as_dict = stage_ep.to_dict()
    alpha = as_dict["agents"]["Alpha"]
    # trait_snapshot should only contain canonical keys, not random_extra
    traits = alpha["trait_snapshot"]
    assert isinstance(traits, dict)
    assert set(traits.keys()).issubset({"resilience", "caution", "agency", "trust_supervisor", "variance"})
    assert "random_extra" not in traits
    assert traits["resilience"] == 0.9
    assert traits["caution"] == 0.1


def test_stage_builder_no_traits_when_empty_or_none_snapshot():
    # Empty dict should result in trait_snapshot=None
    ep_empty = _make_min_episode({})
    stage_ep_empty = build_stage_episode(ep_empty, ep_empty.days, story_arc=None, long_memory=None, character_defs=None, include_narrative=False)
    alpha_empty = stage_ep_empty.to_dict()["agents"]["Alpha"]
    assert alpha_empty["trait_snapshot"] is None

    # None should also result in trait_snapshot=None
    ep_none = _make_min_episode(None)
    stage_ep_none = build_stage_episode(ep_none, ep_none.days, story_arc=None, long_memory=None, character_defs=None, include_narrative=False)
    alpha_none = stage_ep_none.to_dict()["agents"]["Alpha"]
    assert alpha_none["trait_snapshot"] is None
