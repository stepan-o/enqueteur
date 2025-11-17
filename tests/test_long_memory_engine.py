from __future__ import annotations

from loopforge.long_memory import update_long_memory_for_agent
from loopforge.types import AgentLongMemory, EpisodeStoryArc


def _prev(name: str = "Delta") -> AgentLongMemory:
    return AgentLongMemory(
        name=name,
        episodes=0,
        cumulative_stress=0.0,
        cumulative_incidents=0,
        trust_supervisor=0.5,
        self_trust=0.5,
        stability=0.5,
        reactivity=0.5,
        agency=0.5,
    )


def test_baseline_creation_and_ranges():
    mem = update_long_memory_for_agent(
        prev=None,
        name="Delta",
        stress_start=0.2,
        stress_end=0.3,
        guardrail_total=10,
        context_total=5,
        blame_counts={"system": 1},
        blame_timeline=["system"],
        incidents_in_episode=2,
        story_arc=None,
    )
    assert isinstance(mem, AgentLongMemory)
    assert mem.episodes == 1
    assert mem.cumulative_stress >= 0.0
    assert mem.cumulative_incidents >= 0
    for v in [mem.trust_supervisor, mem.self_trust, mem.stability, mem.reactivity, mem.agency]:
        assert 0.0 <= v <= 1.0


def test_supervisor_dominant_blame_lowers_trust_supervisor():
    prev = _prev()
    mem = update_long_memory_for_agent(
        prev,
        name="Delta",
        stress_start=0.2,
        stress_end=0.2,
        guardrail_total=10,
        context_total=0,
        blame_counts={"supervisor": 5},
        blame_timeline=["supervisor"] * 3,
        incidents_in_episode=0,
        story_arc=None,
    )
    assert mem.trust_supervisor < prev.trust_supervisor


def test_self_vs_random_affects_self_trust():
    prev = _prev()
    higher = update_long_memory_for_agent(
        prev,
        name="Delta",
        stress_start=0.2,
        stress_end=0.2,
        guardrail_total=0,
        context_total=10,
        blame_counts={"self": 4},
        blame_timeline=["self"] * 2,
        incidents_in_episode=0,
        story_arc=None,
    )
    assert higher.self_trust > prev.self_trust

    lower = update_long_memory_for_agent(
        prev,
        name="Delta",
        stress_start=0.2,
        stress_end=0.2,
        guardrail_total=0,
        context_total=10,
        blame_counts={"random": 4},
        blame_timeline=["random"] * 2,
        incidents_in_episode=0,
        story_arc=None,
    )
    assert lower.self_trust < prev.self_trust


def test_stability_and_reactivity_with_diversity_and_trend():
    prev = _prev()
    # Falling stress + low diversity -> stability up, reactivity <= prev or small change
    mem1 = update_long_memory_for_agent(
        prev,
        name="Delta",
        stress_start=0.3,
        stress_end=0.1,
        guardrail_total=5,
        context_total=5,
        blame_counts={"system": 3},
        blame_timeline=["system"],
        incidents_in_episode=0,
        story_arc=None,
    )
    assert mem1.stability >= prev.stability

    # Rising stress + high diversity -> stability down, reactivity up
    prev2 = _prev()
    mem2 = update_long_memory_for_agent(
        prev2,
        name="Delta",
        stress_start=0.1,
        stress_end=0.4,
        guardrail_total=5,
        context_total=5,
        blame_counts={"system": 1, "self": 1, "random": 1, "supervisor": 1},
        blame_timeline=["system", "self", "random", "supervisor"],
        incidents_in_episode=0,
        story_arc=None,
    )
    assert mem2.stability <= prev2.stability
    assert mem2.reactivity >= prev2.reactivity


def test_agency_reacts_to_context_and_supervisor():
    prev = _prev()
    # Context-heavy should raise agency
    mem_ctx = update_long_memory_for_agent(
        prev,
        name="Delta",
        stress_start=0.2,
        stress_end=0.2,
        guardrail_total=1,
        context_total=9,
        blame_counts={"self": 3},
        blame_timeline=["self"],
        incidents_in_episode=0,
        story_arc=None,
    )
    assert mem_ctx.agency > prev.agency

    # Guardrail-heavy + supervisor-blame should lower agency
    prev2 = _prev()
    mem_gr = update_long_memory_for_agent(
        prev2,
        name="Delta",
        stress_start=0.2,
        stress_end=0.2,
        guardrail_total=9,
        context_total=1,
        blame_counts={"supervisor": 5},
        blame_timeline=["supervisor"],
        incidents_in_episode=0,
        story_arc=None,
    )
    assert mem_gr.agency < prev2.agency


def test_multi_episode_saturation_and_bounds():
    # Apply strong, consistent signals over many episodes to test clamping and monotonic drift
    mem = None
    for i in range(35):
        mem = update_long_memory_for_agent(
            mem,
            name="Delta",
            stress_start=0.4,   # rising stress
            stress_end=0.6,
            guardrail_total=9,
            context_total=1,
            blame_counts={"supervisor": 5},
            blame_timeline=["supervisor", "system"],
            incidents_in_episode=0,
            story_arc=None,
        )
    assert mem is not None
    assert mem.episodes >= 35
    # All identity fields within [0,1]
    for v in [mem.trust_supervisor, mem.self_trust, mem.stability, mem.reactivity, mem.agency]:
        assert 0.0 <= v <= 1.0
    # At least one field should have drifted significantly toward a bound
    assert (mem.trust_supervisor < 0.45) or (mem.stability < 0.45) or (mem.agency < 0.45)
