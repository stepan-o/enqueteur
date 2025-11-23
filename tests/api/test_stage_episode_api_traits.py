from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import loopforge.api.app as api_app


def test_latest_episode_traits_canonical_only(monkeypatch):
    # Prepare a fake registry with one episode record
    from loopforge.analytics.run_registry import EpisodeRecord

    fake_rows = [
        EpisodeRecord(
            run_id="run-T",
            episode_id="ep-T",
            episode_index=0,
            created_at="2025-01-01T00:00:00+00:00",
            steps_per_day=50,
            days=1,
        )
    ]

    import loopforge.analytics.run_registry as rr
    monkeypatch.setattr(rr, "load_registry", lambda base_dir=None: fake_rows)

    # Monkeypatch analysis to include a trait_snapshot with extra/old keys
    from loopforge.analytics.reporting import DaySummary, EpisodeSummary, AgentDayStats, AgentEpisodeStats

    def fake_analyze_episode_from_record(record, *, action_log_path, supervisor_log_path=None):
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
                trait_snapshot={
                    "resilience": 0.9,
                    "caution": 0.1,
                    "random_extra": 42,
                    "risk_aversion": 0.7,  # old key should be ignored by Stage builder
                },
            )
        }
        return EpisodeSummary(days=[day0], agents=agents, tension_trend=[0.2], episode_id=record.episode_id, run_id=record.run_id, episode_index=record.episode_index)

    import loopforge.analytics.analysis_api as analysis_api
    monkeypatch.setattr(analysis_api, "analyze_episode_from_record", fake_analyze_episode_from_record)

    client = TestClient(api_app.app)
    resp = client.get("/episodes/latest")
    assert resp.status_code == 200
    data = resp.json()
    alpha = data["agents"]["Alpha"]
    traits = alpha.get("trait_snapshot")
    assert isinstance(traits, dict)
    # Only canonical keys should be present
    allowed = {"resilience", "caution", "agency", "trust_supervisor", "variance"}
    assert set(traits.keys()).issubset(allowed)
    assert "random_extra" not in traits
    assert "risk_aversion" not in traits
    # Values passed through
    assert traits["resilience"] == 0.9
    assert traits["caution"] == 0.1
