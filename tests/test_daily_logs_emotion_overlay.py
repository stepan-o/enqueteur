from __future__ import annotations

from loopforge.reporting import DaySummary, AgentDayStats
from loopforge.schema.types import AgentEmotionState
from loopforge.daily_logs import build_daily_log


def _day(name: str, role: str, avg_stress: float, emotion: AgentEmotionState | None):
    ds = DaySummary(
        day_index=0,
        perception_mode="accurate",
        tension_score=0.2,
        agent_stats={
            name: AgentDayStats(name=name, role=role, guardrail_count=1, context_count=0, avg_stress=avg_stress)
        },
        total_incidents=0,
        beliefs={},
        belief_attributions={},
        reflection_states={},
        emotion_states={},
    )
    if emotion is not None:
        ds.emotion_states[name] = emotion
    return ds


def test_emotion_bullet_appears_when_emotion_present():
    name = "Delta"
    ds = _day(name, "optimizer", 0.25, AgentEmotionState(mood="uneasy", certainty="doubtful", energy="steady"))
    log = build_daily_log(ds, day_index=0, previous_day_summary=None)
    text = "\n".join([log.intro] + sum(log.agent_beats.values(), []) + log.general_beats + [log.closing])
    assert "Emotion:" in text
    assert ("uneasy" in text) or ("unsure" in text)


def test_no_emotion_bullet_when_state_missing():
    name = "Delta"
    ds = _day(name, "optimizer", 0.25, None)
    log = build_daily_log(ds, day_index=0, previous_day_summary=None)
    text = "\n".join([log.intro] + sum(log.agent_beats.values(), []) + log.general_beats + [log.closing])
    assert "Emotion:" not in text


essentials = [
    (AgentEmotionState(mood="tense", certainty="confident", energy="wired"), "wired"),
    (AgentEmotionState(mood="calm", certainty="confident", energy="drained"), "spent"),
]


def test_distinct_emotion_wording_for_different_combos():
    name = "Delta"
    texts = []
    for emo, expect in essentials:
        ds = _day(name, "optimizer", 0.30, emo)
        log = build_daily_log(ds, day_index=0, previous_day_summary=None)
        t = "\n".join([log.intro] + sum(log.agent_beats.values(), []) + log.general_beats + [log.closing])
        texts.append(t)
        assert expect in t
    # Ensure the two bullets differ in wording
    assert texts[0] != texts[1]
