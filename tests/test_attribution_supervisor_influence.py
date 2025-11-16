import pytest

from loopforge.attribution import derive_belief_attribution
from loopforge.reporting import AgentDayStats


def test_attribution_blames_supervisor_on_rising_stress_and_high_activity():
    """
    The attribution engine should blame the supervisor when:
    - stress increased,
    - activity_count_high ≈ supervisor_activity >= 0.6,
    - no incidents,
    - guardrail-heavy behavior.
    """

    prev = AgentDayStats(
        name="Delta",
        role="optimizer",
        guardrail_count=10,
        context_count=0,
        avg_stress=0.10,
    )

    curr = AgentDayStats(
        name="Delta",
        role="optimizer",
        guardrail_count=10,
        context_count=0,
        avg_stress=0.20,
    )

    # Low supervisor activity should *not* trigger supervisor blame.
    low = derive_belief_attribution(
        agent_day_stats=curr,
        previous_stats=prev,
        supervisor_activity=0.1,
        tension=0.3,
    )
    assert low.cause != "supervisor"

    # High supervisor activity (>=0.6) + rising stress → supervisor blame.
    high = derive_belief_attribution(
        agent_day_stats=curr,
        previous_stats=prev,
        supervisor_activity=0.9,
        tension=0.3,
    )
    assert high.cause == "supervisor"
