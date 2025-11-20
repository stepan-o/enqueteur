from loopforge.daily_logs import build_psych_snapshot_line, build_psych_snapshot_block
from loopforge.reporting import DaySummary, AgentDayStats
from loopforge.schema.types import BeliefAttribution, AgentEmotionState


def _mk_stats(name: str, role: str = "qa", stress: float = 0.0, g: int = 0, c: int = 0) -> AgentDayStats:
    return AgentDayStats(name=name, role=role, avg_stress=stress, guardrail_count=g, context_count=c)


def test_build_psych_snapshot_line_basic():
    # Stress band mapping via line output: low <0.08, mid 0.08–0.30, high >0.30
    stats_low = _mk_stats("Nova", stress=0.05)
    stats_mid = _mk_stats("Delta", stress=0.10)
    stats_high = _mk_stats("Sprocket", stress=0.35)

    attr = BeliefAttribution(cause="system", confidence=0.7, rationale="test")
    emo = AgentEmotionState(mood="uneasy", certainty="confident", energy="steady")

    line_low = build_psych_snapshot_line("Nova", stats_low, attr, emo)
    assert "stress=low" in line_low
    assert "attribution=system (conf=0.70)" in line_low
    assert "mood=uneasy" in line_low and "certainty=confident" in line_low and "energy=steady" in line_low

    line_mid = build_psych_snapshot_line("Delta", stats_mid, attr, emo)
    assert "stress=mid" in line_mid

    line_high = build_psych_snapshot_line("Sprocket", stats_high, attr, emo)
    assert "stress=high" in line_high


def test_build_psych_snapshot_block_ordering_and_content():
    # Construct synthetic DaySummary with 3 agents out of order
    stats_map = {
        "Zeta": _mk_stats("Zeta", stress=0.09),  # mid
        "Alpha": _mk_stats("Alpha", stress=0.02),  # low
        "Mira": _mk_stats("Mira", stress=0.40),   # high
    }
    day = DaySummary(
        day_index=0,
        perception_mode="accurate",
        tension_score=0.0,
        agent_stats=stats_map,
        total_incidents=0,
        beliefs={},
        belief_attributions={
            "Zeta": BeliefAttribution(cause="random", confidence=0.2, rationale="flat"),
            "Alpha": BeliefAttribution(cause="self", confidence=0.7, rationale="incidents"),
            "Mira": BeliefAttribution(cause="supervisor", confidence=0.7, rationale="rising"),
        },
        reflection_states={},
        emotion_states={
            "Zeta": AgentEmotionState(mood="uneasy", certainty="doubtful", energy="steady"),
            "Alpha": AgentEmotionState(mood="calm", certainty="uncertain", energy="drained"),
            "Mira": AgentEmotionState(mood="tense", certainty="confident", energy="wired"),
        },
    )

    lines = build_psych_snapshot_block(day)

    # Deterministic ordering: Alpha, Mira, Zeta
    assert len(lines) == 3
    assert lines[0].startswith("Alpha:")
    assert lines[1].startswith("Mira:")
    assert lines[2].startswith("Zeta:")

    # Content spot checks
    assert "stress=low" in lines[0]
    assert "attribution=self (conf=0.70)" in lines[0]
    assert "mood=calm" in lines[0] and "certainty=uncertain" in lines[0] and "energy=drained" in lines[0]

    assert "stress=high" in lines[1]
    assert "attribution=supervisor (conf=0.70)" in lines[1]
    assert "mood=tense" in lines[1] and "certainty=confident" in lines[1] and "energy=wired" in lines[1]

    assert "stress=mid" in lines[2]
    assert "attribution=random (conf=0.20)" in lines[2]
    assert "mood=uneasy" in lines[2] and "certainty=doubtful" in lines[2] and "energy=steady" in lines[2]
