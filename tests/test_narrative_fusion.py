from __future__ import annotations

from types import SimpleNamespace

from loopforge.narrative.narrative_fusion import build_day_narrative_kernel, DayNarrativeKernel
from loopforge.reporting import DaySummary, AgentDayStats


def _mk_day(
    *,
    day_index: int = 0,
    tension: float = 0.0,
    supervisor_activity: float = 0.0,
    agents: dict[str, AgentDayStats] | None = None,
    reflection_states: dict | None = None,
    emotion_states: dict | None = None,
    beliefs: dict | None = None,
    belief_attributions: dict | None = None,
) -> DaySummary:
    return DaySummary(
        day_index=day_index,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats=agents or {},
        total_incidents=0,
        supervisor_activity=supervisor_activity,
        beliefs=beliefs or {},
        belief_attributions=belief_attributions or {},
        reflection_states=reflection_states or {},
        emotion_states=emotion_states or {},
    )


def test_minimal_day_summary_stable_kernel():
    d = _mk_day(day_index=0, tension=0.0, supervisor_activity=0.0)

    k = build_day_narrative_kernel(d)

    assert isinstance(k, DayNarrativeKernel)
    assert k.day_index == 0
    assert 0.0 <= k.global_pressure <= 1.0
    assert k.supervisor_tone in {"supportive", "neutral", "concerned", "critical"}
    # With minimal inputs, vectors should be zeros and supportive tone
    assert set(k.distortion_vector.keys()) == {"catastrophizing", "confirmation_bias", "self_blame"}
    assert all(abs(v) < 1e-12 for v in k.distortion_vector.values())
    assert set(k.memory_drift_vector.keys()) == {"coherence_drop", "recall_mismatch", "memory_drift"}
    assert all(abs(v) < 1e-12 for v in k.memory_drift_vector.values())
    assert k.supervisor_tone == "supportive"
    assert isinstance(k.synthesis_line, str) and len(k.synthesis_line) > 0
    # Deterministic phrasing fragments
    assert "Pressure is low" in k.synthesis_line
    assert "Supervisor tone" in k.synthesis_line


def test_high_stress_and_critical_supervisor_mentions_pressure_and_tone():
    agents = {
        "Delta": AgentDayStats(name="Delta", role="optimizer", avg_stress=0.90, guardrail_count=8, context_count=2),
        "Nova": AgentDayStats(name="Nova", role="qa", avg_stress=0.20, guardrail_count=1, context_count=9),
    }
    d = _mk_day(day_index=1, tension=0.90, supervisor_activity=0.95, agents=agents)

    k = build_day_narrative_kernel(d)

    assert k.global_pressure >= 0.66  # high band
    assert k.supervisor_tone == "critical"
    assert "Pressure is high" in k.synthesis_line
    assert "Supervisor tone turned critical" in k.synthesis_line
    # Dominant fragility should register a crisis-like label (likely stressed/rigid)
    assert k.dominant_fragility in {"stressed", "rigid", "confused", "avoidant", "balanced"}


def test_high_memory_drift_exposes_nonzero_memory_vector():
    # Provide a reflection state with a high memory drift signal
    ref_states = {
        "Delta": SimpleNamespace(memory_drift=0.8),
    }
    d = _mk_day(day_index=2, tension=0.2, supervisor_activity=0.1, reflection_states=ref_states)

    k = build_day_narrative_kernel(d)

    assert k.memory_drift_vector["memory_drift"] > 0.5
    # With drift high and low stress, fragility could be "confused" or "balanced"
    assert k.dominant_fragility in {"confused", "balanced", "avoidant", "rigid", "stressed"}


def test_missing_fields_no_crash_and_deterministic():
    # Omit beliefs/attributions/emotions — builder must not crash
    agents = {
        "Sprocket": AgentDayStats(name="Sprocket", role="maintenance", avg_stress=0.30, guardrail_count=5, context_count=5)
    }
    d = _mk_day(day_index=0, tension=0.3, supervisor_activity=0.3, agents=agents)

    k1 = build_day_narrative_kernel(d)
    k2 = build_day_narrative_kernel(d)

    # Stable repeatable outputs
    assert k1 == k2
    assert isinstance(k1.synthesis_line, str) and len(k1.synthesis_line) > 0
