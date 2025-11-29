from __future__ import annotations

from loopforge.analytics.reporting import DaySummary, AgentDayStats
from loopforge.schema.types import AgentEmotionState, AgentReflectionState
from loopforge.narrative.narrative_viewer import build_day_narrative


def _ds_with(name: str, role: str, avg_stress: float,
             emotion: AgentEmotionState | None = None,
             reflect: AgentReflectionState | None = None) -> DaySummary:
    ds = DaySummary(
        day_index=0,
        perception_mode="accurate",
        tension_score=0.2,
        agent_stats={
            name: AgentDayStats(name=name, role=role, guardrail_count=0, context_count=0, avg_stress=avg_stress)
        },
        total_incidents=0,
        beliefs={},
        belief_attributions={},
        reflection_states={},
        emotion_states={},
    )
    if reflect is not None:
        ds.reflection_states[name] = reflect
    if emotion is not None:
        ds.emotion_states[name] = emotion
    return ds


def test_intro_variant_wound_tight_when_tense_and_wired():
    name = "Delta"
    ds = _ds_with(
        name=name,
        role="optimizer",
        avg_stress=0.30,
        emotion=AgentEmotionState(mood="tense", certainty="confident", energy="wired"),
    )
    dn = build_day_narrative(ds, day_index=0, previous_day_summary=None)
    # Find this agent's beat
    beat = next(b for b in dn.agent_beats if b.name == name)
    assert "wound a little tight" in beat.intro


def test_intro_variant_relaxed_when_calm_and_drained():
    name = "Delta"
    ds = _ds_with(
        name=name,
        role="optimizer",
        avg_stress=0.05,
        emotion=AgentEmotionState(mood="calm", certainty="confident", energy="drained"),
    )
    dn = build_day_narrative(ds, day_index=0, previous_day_summary=None)
    beat = next(b for b in dn.agent_beats if b.name == name)
    assert "drifts into the shift almost relaxed" in beat.intro


def test_closing_variant_rising_carries_weight_and_falling_is_calm():
    name = "Delta"
    # Rising trend case
    ds_rise = _ds_with(
        name=name,
        role="optimizer",
        avg_stress=0.20,
        emotion=AgentEmotionState(mood="tense", certainty="confident", energy="steady"),
        reflect=AgentReflectionState(stress_trend="rising", rulebook_reliance=0.6, supervisor_presence=0.0),
    )
    dn_rise = build_day_narrative(ds_rise, day_index=0, previous_day_summary=None)
    beat_rise = next(b for b in dn_rise.agent_beats if b.name == name)
    assert "carrying some weight" in beat_rise.closing_line

    # Falling trend with very low stress → calm nothing sticking
    ds_fall = _ds_with(
        name=name,
        role="optimizer",
        avg_stress=0.05,
        emotion=AgentEmotionState(mood="calm", certainty="confident", energy="steady"),
        reflect=AgentReflectionState(stress_trend="falling", rulebook_reliance=0.6, supervisor_presence=0.0),
    )
    dn_fall = build_day_narrative(ds_fall, day_index=0, previous_day_summary=None)
    beat_fall = next(b for b in dn_fall.agent_beats if b.name == name)
    assert "calm, nothing sticking" in beat_fall.closing_line


def test_backward_compat_without_states_keeps_default_intro():
    name = "Delta"
    # No reflection or emotion states → default intro based on stress bands
    ds = _ds_with(
        name=name,
        role="optimizer",
        avg_stress=0.20,
        emotion=None,
        reflect=None,
    )
    dn = build_day_narrative(ds, day_index=0, previous_day_summary=None)
    beat = next(b for b in dn.agent_beats if b.name == name)
    assert "comes online steady but alert" in beat.intro
