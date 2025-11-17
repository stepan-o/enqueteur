from __future__ import annotations

import pytest

from loopforge.reporting import AgentDayStats
from loopforge.types import AgentReflectionState, AgentEmotionState, BeliefAttribution
from loopforge.emotion_model import derive_emotion_state


def _stats(avg_stress: float) -> AgentDayStats:
    return AgentDayStats(
        name="Delta",
        role="optimizer",
        guardrail_count=10,
        context_count=0,
        avg_stress=avg_stress,
    )


def _reflection(trend: str) -> AgentReflectionState:
    return AgentReflectionState(
        stress_trend=trend,
        rulebook_reliance=0.8,
        supervisor_presence=0.2,
    )


def _attr(cause: str) -> BeliefAttribution:
    return BeliefAttribution(
        cause=cause,
        confidence=0.7,
        rationale="",
    )


# Mood tests

def test_mood_calm_on_low_stress():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.05),
        reflection_state=_reflection("flat"),
        attribution=_attr("random"),
    )
    assert state.mood == "calm"


def test_mood_tense_on_mid_stress_rising():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.25),
        reflection_state=_reflection("rising"),
        attribution=_attr("system"),
    )
    assert state.mood == "tense"


def test_mood_uneasy_on_mid_stress_non_rising():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.25),
        reflection_state=_reflection("falling"),
        attribution=_attr("system"),
    )
    assert state.mood == "uneasy"


def test_mood_brittle_on_high_stress_rising():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.50),
        reflection_state=_reflection("rising"),
        attribution=_attr("system"),
    )
    assert state.mood == "brittle"


# Certainty tests

def test_certainty_confident_when_cause_is_concrete_and_trend_known():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.30),
        reflection_state=_reflection("falling"),
        attribution=_attr("system"),
    )
    assert state.certainty == "confident"


def test_certainty_doubtful_when_random_and_not_falling():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.30),
        reflection_state=_reflection("rising"),
        attribution=_attr("random"),
    )
    assert state.certainty == "doubtful"


def test_certainty_uncertain_when_random_and_falling():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.30),
        reflection_state=_reflection("falling"),
        attribution=_attr("random"),
    )
    assert state.certainty == "uncertain"


def test_certainty_uncertain_when_unknown_cause():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.30),
        reflection_state=_reflection("flat"),
        attribution=None,
    )
    assert state.certainty == "uncertain"


# Energy tests

def test_energy_drained_low_stress():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.05),
        reflection_state=_reflection("unknown"),
        attribution=_attr("random"),
    )
    assert state.energy == "drained"


def test_energy_steady_mid_stress():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.20),
        reflection_state=_reflection("unknown"),
        attribution=_attr("random"),
    )
    assert state.energy == "steady"


def test_energy_wired_high_stress():
    state = derive_emotion_state(
        agent_day_stats=_stats(0.50),
        reflection_state=_reflection("unknown"),
        attribution=_attr("random"),
    )
    assert state.energy == "wired"
