from __future__ import annotations

from loopforge.reporting import summarize_day, DaySummary
from loopforge.schema.types import ActionLogEntry, AgentEmotionState


def _mk_entry(step: int, name: str, role: str, mode: str, *, stress: float = 0.0):
    return ActionLogEntry(
        step=step,
        agent_name=name,
        role=role,
        mode=mode,
        intent="",
        move_to=None,
        targets=[],
        riskiness=0.0,
        narrative="",
        raw_action={},
        perception={
            "emotions": {"stress": stress, "curiosity": 0.5, "satisfaction": 0.5},
            "perception_mode": "accurate",
        },
        outcome=None,
    )


def test_summarize_day_populates_emotion_states():
    # Build a minimal synthetic day with one agent and multiple steps
    entries = [
        _mk_entry(0, "Delta", "optimizer", "guardrail", stress=0.30),
        _mk_entry(1, "Delta", "optimizer", "guardrail", stress=0.30),
    ]

    day: DaySummary = summarize_day(
        day_index=0,
        entries=entries,
        reflections_by_agent=None,
        previous_day_stats=None,
        supervisor_activity=0.0,
    )

    assert isinstance(day, DaySummary)
    assert hasattr(day, "emotion_states")
    assert isinstance(day.emotion_states, dict)
    assert "Delta" in day.emotion_states

    es = day.emotion_states["Delta"]
    assert isinstance(es, AgentEmotionState)
    assert es.mood in {"calm", "uneasy", "tense", "brittle"}
    assert es.certainty in {"confident", "uncertain", "doubtful"}
    assert es.energy in {"drained", "steady", "wired"}
