from __future__ import annotations

import json
from typing import Dict, List

from loopforge.analytics.reporting import (
    DaySummary,
    AgentDayStats,
    summarize_episode,
)
from loopforge.schema.types import BeliefAttribution
from loopforge.narrative.episode_recaps import build_episode_recap
from loopforge.analytics.analysis_api import episode_summary_to_dict
from loopforge.schema.types import AgentLongMemory


def _mk_day(
    idx: int,
    agent_specs: Dict[str, Dict[str, float]],
    *,
    tension: float = 0.2,
    incidents: int = 1,
    attributions: Dict[str, str] | None = None,
) -> DaySummary:
    """Build a DaySummary with provided per-agent specs.

    agent_specs: name -> {"role","avg_stress","g","c"}
    attributions: name -> cause (canonical or "unknown" via omission)
    """
    stats: Dict[str, AgentDayStats] = {}
    for name, spec in agent_specs.items():
        stats[name] = AgentDayStats(
            name=name,
            role=str(spec.get("role", "operator")),
            guardrail_count=int(spec.get("g", 0)),
            context_count=int(spec.get("c", 0)),
            avg_stress=float(spec.get("avg_stress", 0.0)),
        )

    ds = DaySummary(
        day_index=idx,
        perception_mode="accurate",
        tension_score=float(tension),
        agent_stats=stats,
        total_incidents=int(incidents),
        beliefs={},
        belief_attributions={},
        reflection_states={},
        emotion_states={},
    )

    # Attach belief attributions (omit some to force "unknown" in timeline)
    if attributions:
        for name, cause in attributions.items():
            if cause in {"self", "supervisor", "system", "random"}:
                ds.belief_attributions[name] = BeliefAttribution(
                    cause=cause,
                    confidence=0.7 if cause in {"self", "supervisor"} else 0.4,
                    rationale="",
                )
            # any non-canonical or explicit "unknown" is skipped → timeline gets "unknown"
    return ds


def _seed_previous_long_memory(names: List[str]) -> Dict[str, AgentLongMemory]:
    """Create a previous_long_memory map pre-biased to cross recap thresholds.

    Thresholds in recap (episode_recaps.py):
      - agency > 0.6 and stability > 0.5
      - trust_supervisor < 0.4 and self_trust < 0.4
      - stability < 0.4 and reactivity > 0.6
    """
    seed: Dict[str, AgentLongMemory] = {}
    for n in names:
        # Baseline entries
        episodes = 1
        mem = AgentLongMemory(
            name=n,
            episodes=episodes,
            cumulative_stress=0.0,
            cumulative_incidents=0,
            trust_supervisor=0.5,
            self_trust=0.5,
            stability=0.5,
            reactivity=0.5,
            agency=0.5,
        )
        seed[n] = mem

    # Bias three distinct agents to satisfy recap line templates deterministically
    if "Delta" in seed:
        seed["Delta"].agency = 0.62
        seed["Delta"].stability = 0.52
    if "Nova" in seed:
        seed["Nova"].trust_supervisor = 0.35
        seed["Nova"].self_trust = 0.35
    if "Sprocket" in seed:
        seed["Sprocket"].stability = 0.38
        seed["Sprocket"].reactivity = 0.65
    # Leave others near baseline; engine may drift them slightly
    return seed


def test_five_agent_long_memory_stress_episode() -> None:
    # Define 5 agents with roles
    roles = {
        "Delta": "optimizer",
        "Nova": "qa",
        "Sprocket": "maintenance",
        "Helix": "analyst",
        "Vim": "operator",
    }

    # Build 3–4 days with mixed stress patterns and uneven guardrail/context
    # Day 0 (baseline different stresses)
    day0_specs = {
        "Delta": {"role": roles["Delta"], "avg_stress": 0.40, "g": 8, "c": 1},  # guardrail ≫ context
        "Nova": {"role": roles["Nova"], "avg_stress": 0.10, "g": 1, "c": 8},   # context ≫ guardrail
        "Sprocket": {"role": roles["Sprocket"], "avg_stress": 0.20, "g": 5, "c": 5},  # balanced
        "Helix": {"role": roles["Helix"], "avg_stress": 0.15, "g": 10, "c": 0},       # very high guardrail
        "Vim": {"role": roles["Vim"], "avg_stress": 0.12, "g": 0, "c": 6},            # very low guardrail
    }
    day0_attr = {
        "Delta": "system",
        "Nova": "self",
        "Sprocket": "random",
        "Helix": "supervisor",
        # Vim attribution omitted to inject "unknown" in the timeline
    }
    d0 = _mk_day(0, day0_specs, tension=0.30, incidents=2, attributions=day0_attr)

    # Day 1 (falling Delta, rising Nova, flat Sprocket, oscillating Helix, small rise Vim)
    day1_specs = {
        "Delta": {"role": roles["Delta"], "avg_stress": 0.30, "g": 9, "c": 1},
        "Nova": {"role": roles["Nova"], "avg_stress": 0.20, "g": 1, "c": 9},
        "Sprocket": {"role": roles["Sprocket"], "avg_stress": 0.20, "g": 6, "c": 6},
        "Helix": {"role": roles["Helix"], "avg_stress": 0.30, "g": 12, "c": 0},
        "Vim": {"role": roles["Vim"], "avg_stress": 0.18, "g": 1, "c": 7},
    }
    day1_attr = {
        "Delta": "system",
        "Nova": "system",
        "Sprocket": "random",
        # Helix attribution omitted this day (forces another "unknown")
        "Vim": "self",
    }
    d1 = _mk_day(1, day1_specs, tension=0.15, incidents=1, attributions=day1_attr)

    # Day 2
    day2_specs = {
        "Delta": {"role": roles["Delta"], "avg_stress": 0.20, "g": 10, "c": 1},
        "Nova": {"role": roles["Nova"], "avg_stress": 0.30, "g": 2, "c": 10},
        "Sprocket": {"role": roles["Sprocket"], "avg_stress": 0.20, "g": 5, "c": 5},
        "Helix": {"role": roles["Helix"], "avg_stress": 0.20, "g": 11, "c": 0},
        "Vim": {"role": roles["Vim"], "avg_stress": 0.20, "g": 1, "c": 8},
    }
    day2_attr = {
        "Delta": "system",
        "Nova": "supervisor",
        "Sprocket": "system",
        "Helix": "supervisor",
        "Vim": "random",
    }
    d2 = _mk_day(2, day2_specs, tension=0.10, incidents=3, attributions=day2_attr)

    # Day 3 (optional fourth day to accentuate trends)
    day3_specs = {
        "Delta": {"role": roles["Delta"], "avg_stress": 0.15, "g": 10, "c": 1},
        "Nova": {"role": roles["Nova"], "avg_stress": 0.40, "g": 2, "c": 11},
        "Sprocket": {"role": roles["Sprocket"], "avg_stress": 0.20, "g": 5, "c": 5},
        "Helix": {"role": roles["Helix"], "avg_stress": 0.25, "g": 12, "c": 0},
        "Vim": {"role": roles["Vim"], "avg_stress": 0.20, "g": 1, "c": 8},
    }
    day3_attr = {
        "Delta": "system",
        "Nova": "self",
        "Sprocket": "random",
        # leave Helix/Vim omitted to keep some "unknown" in the mix
    }
    d3 = _mk_day(3, day3_specs, tension=0.12, incidents=2, attributions=day3_attr)

    day_summaries = [d0, d1, d2, d3]

    # Seed previous_long_memory to cross deterministic recap thresholds
    prev_long = _seed_previous_long_memory(list(roles.keys()))

    # Summarize episode with seeded previous memory (baseline creation + drift)
    ep = summarize_episode(day_summaries, previous_long_memory=prev_long)

    # Invariants: long_memory exists and contains all 5 agents
    assert ep.long_memory is not None
    assert set(ep.long_memory.keys()) == set(roles.keys())

    # Check memory fields bounds and counts
    for name, mem in ep.long_memory.items():
        assert isinstance(mem.episodes, int) and mem.episodes >= 1
        assert isinstance(mem.cumulative_incidents, int) and mem.cumulative_incidents >= 0
        for fld in ("trust_supervisor", "self_trust", "stability", "reactivity", "agency"):
            v = float(getattr(mem, fld))
            assert 0.0 <= v <= 1.0

    # Recap should include STORY ARC and MEMORY DRIFT blocks
    recap = build_episode_recap(ep, ep.days, characters={})
    assert recap.story_arc_lines is not None and len(recap.story_arc_lines) >= 1
    # With seeded previous memory, at least one memory line should be produced
    assert recap.memory_lines is not None and len(recap.memory_lines) >= 1

    # Export dict contains long_memory with all five agents and is JSON-serializable
    export = episode_summary_to_dict(ep)
    assert "long_memory" in export
    lm = export["long_memory"]
    assert lm is None or isinstance(lm, dict)
    # When present, ensure all names exist and values are JSON-safe
    if isinstance(lm, dict):
        assert set(lm.keys()) == set(roles.keys())
        s = json.dumps(export)  # full export must be serializable
        assert isinstance(s, str)
