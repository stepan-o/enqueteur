from __future__ import annotations

from types import SimpleNamespace
from typing import List

from fastapi.testclient import TestClient

import loopforge.api.app as api_app


def test_list_and_detail_endpoints(monkeypatch):
    # Prepare a fake registry with one episode record
    from loopforge.analytics.run_registry import EpisodeRecord

    fake_rows: List[EpisodeRecord] = [
        EpisodeRecord(
            run_id="run-X",
            episode_id="ep-X",
            episode_index=1,
            created_at="2025-01-01T00:00:00+00:00",
            steps_per_day=50,
            days=2,
        )
    ]

    # Monkeypatch load_registry to return our fake rows
    import loopforge.analytics.run_registry as rr
    monkeypatch.setattr(rr, "load_registry", lambda base_dir=None: fake_rows)

    # Monkeypatch analysis to return a minimal EpisodeSummary and days
    from loopforge.analytics.reporting import DaySummary, EpisodeSummary, AgentDayStats, AgentEpisodeStats

    def fake_analyze_episode_from_record(record, *, action_log_path, supervisor_log_path=None):
        # Build minimal episode summary aligned with builder expectations
        agent_stats = {
            "Alpha": AgentDayStats(name="Alpha", role="scout", guardrail_count=1, context_count=2, avg_stress=0.3),
            "Beta": AgentDayStats(name="Beta", role="worker", guardrail_count=0, context_count=1, avg_stress=0.1),
        }
        day0 = DaySummary(day_index=0, perception_mode="accurate", tension_score=0.2, agent_stats=agent_stats, total_incidents=0, supervisor_activity=0.0)
        day1 = DaySummary(day_index=1, perception_mode="accurate", tension_score=0.4, agent_stats=agent_stats, total_incidents=1, supervisor_activity=0.1)
        agents = {
            "Alpha": AgentEpisodeStats(
                name="Alpha", role="scout", guardrail_total=2, context_total=3, trait_deltas={}, stress_start=0.2, stress_end=0.4, representative_reflection=None, visual="", vibe="", tagline="", trait_snapshot=None
            ),
            "Beta": AgentEpisodeStats(
                name="Beta", role="worker", guardrail_total=0, context_total=2, trait_deltas={}, stress_start=0.1, stress_end=0.2, representative_reflection=None, visual="", vibe="", tagline="", trait_snapshot=None
            ),
        }
        ep = EpisodeSummary(days=[day0, day1], agents=agents, tension_trend=[0.2, 0.4], episode_id=record.episode_id, run_id=record.run_id, episode_index=record.episode_index)
        # Attach optional arc/memory placeholders to exercise mapping
        ep.story_arc = SimpleNamespace(title="Rising Tension")  # will be converted fail-soft
        ep.long_memory = None
        return ep

    import loopforge.analytics.analysis_api as analysis_api
    monkeypatch.setattr(analysis_api, "analyze_episode_from_record", fake_analyze_episode_from_record)

    # Monkeypatch narrative to stable outputs
    import loopforge.stage.builder as builder_mod

    def fake_build_day_narrative(day_summary, day_index, previous_day_summary=None):
        return SimpleNamespace(
            agent_beats=[SimpleNamespace(name="Alpha", intro="I", perception_line="see", actions_line="do", closing_line="end")],
            day_intro=f"Day {day_index} intro",
            supervisor_line="Supervisor speaks",
            day_outro=f"Day {day_index} outro",
        )

    def fake_build_episode_recap(episode_summary, day_summaries, character_defs):
        return SimpleNamespace(intro="Recap intro", per_agent_blurbs={"Alpha": "Alpha blurb"}, closing="Recap end")

    monkeypatch.setattr(builder_mod, "build_day_narrative", fake_build_day_narrative)
    monkeypatch.setattr(builder_mod, "build_episode_recap", fake_build_episode_recap)

    client = TestClient(api_app.app)

    # List endpoint
    resp = client.get("/episodes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 1
    assert data[0]["episode_id"] == "ep-X"

    # Detail endpoint
    resp2 = client.get("/episodes/ep-X")
    assert resp2.status_code == 200
    episode_json = resp2.json()
    assert episode_json["episode_id"] == "ep-X"
    assert episode_json["tension_trend"] == [0.2, 0.4]
    assert episode_json.get("stage_version") == 1
    assert "days" in episode_json and isinstance(episode_json["days"], list)
    assert "agents" in episode_json and isinstance(episode_json["agents"], dict)
