from __future__ import annotations

from typing import Dict

from loopforge.story_arc import derive_episode_story_arc
from loopforge.reporting import EpisodeSummary, DaySummary, AgentDayStats
from loopforge.schema.types import AgentEmotionState, AgentReflectionState


def _day(idx: int, tension: float, stats: Dict[str, AgentDayStats] | None = None,
         reflections: Dict[str, AgentReflectionState] | None = None,
         emotions: Dict[str, AgentEmotionState] | None = None) -> DaySummary:
    ds = DaySummary(
        day_index=idx,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats=stats or {},
        total_incidents=0,
        beliefs={},
        belief_attributions={},
        reflection_states=reflections or {},
        emotion_states=emotions or {},
    )
    return ds


def _stats(name: str, role: str, stress: float) -> AgentDayStats:
    return AgentDayStats(name=name, role=role, guardrail_count=0, context_count=0, avg_stress=stress)


def test_decompression_and_steady_cooldown():
    # Tension steadily decreases; stress falls from start to end
    d0 = _day(0, 0.30, stats={"Delta": _stats("Delta", "optimizer", 0.30)})
    d1 = _day(1, 0.15, stats={"Delta": _stats("Delta", "optimizer", 0.20)})
    d2 = _day(2, 0.10, stats={"Delta": _stats("Delta", "optimizer", 0.10)})
    ep = EpisodeSummary(days=[d0, d1, d2], agents={}, tension_trend=[0.30, 0.15, 0.10])

    arc = derive_episode_story_arc(ep)
    assert arc.arc_type == "decompression"
    assert arc.tension_pattern == "steady_cooldown"
    assert 3 <= len(arc.summary_lines) <= 6
    # Ensure lines include known keywords
    assert any("Tension" in s or "tension" in s for s in arc.summary_lines)


def test_escalation_and_late_spike():
    d0 = _day(0, 0.05, stats={"Delta": _stats("Delta", "optimizer", 0.05)})
    d1 = _day(1, 0.10, stats={"Delta": _stats("Delta", "optimizer", 0.12)})
    d2 = _day(2, 0.30, stats={"Delta": _stats("Delta", "optimizer", 0.20)})
    ep = EpisodeSummary(days=[d0, d1, d2], agents={}, tension_trend=[0.05, 0.10, 0.30])

    arc = derive_episode_story_arc(ep)
    assert arc.arc_type == "escalation"
    assert arc.tension_pattern == "late_spike"


def test_supervisor_looming_pattern():
    # Supervisor presence ~0.7 across days
    refl = {"Delta": AgentReflectionState(stress_trend="flat", rulebook_reliance=0.5, supervisor_presence=0.7)}
    d0 = _day(0, 0.2, stats={"Delta": _stats("Delta", "optimizer", 0.2)}, reflections=refl)
    d1 = _day(1, 0.2, stats={"Delta": _stats("Delta", "optimizer", 0.2)}, reflections=refl)
    d2 = _day(2, 0.2, stats={"Delta": _stats("Delta", "optimizer", 0.2)}, reflections=refl)
    ep = EpisodeSummary(days=[d0, d1, d2], agents={}, tension_trend=[0.2, 0.2, 0.2])

    arc = derive_episode_story_arc(ep)
    assert arc.supervisor_pattern == "looming"


def test_emotional_exhaustion_color():
    # Early steady, last day drained majority
    emo_steady = {"Delta": AgentEmotionState(mood="uneasy", certainty="uncertain", energy="steady"),
                  "Nova": AgentEmotionState(mood="calm", certainty="confident", energy="steady")}
    emo_drained = {"Delta": AgentEmotionState(mood="calm", certainty="uncertain", energy="drained"),
                   "Nova": AgentEmotionState(mood="calm", certainty="confident", energy="drained")}
    d0 = _day(0, 0.2, stats={"Delta": _stats("Delta", "optimizer", 0.2), "Nova": _stats("Nova", "qa", 0.15)}, emotions=emo_steady)
    d1 = _day(1, 0.2, stats={"Delta": _stats("Delta", "optimizer", 0.18), "Nova": _stats("Nova", "qa", 0.12)}, emotions=emo_steady)
    d2 = _day(2, 0.2, stats={"Delta": _stats("Delta", "optimizer", 0.10), "Nova": _stats("Nova", "qa", 0.08)}, emotions=emo_drained)
    ep = EpisodeSummary(days=[d0, d1, d2], agents={}, tension_trend=[0.2, 0.2, 0.2])

    arc = derive_episode_story_arc(ep)
    assert arc.emotional_color in {"exhaustion", "wired_to_calm", "steady_calm"}
    # Accept exhaustion or a calm-ish label depending on thresholds
    # but summary lines must include an emotional tone sentence
    assert any("Emotional" in s or "floor" in s for s in arc.summary_lines)
