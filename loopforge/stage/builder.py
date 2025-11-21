from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Optional, Mapping, Any

from loopforge.analytics.reporting import (
    EpisodeSummary,
    DaySummary,
)
from loopforge.schema.types import EpisodeStoryArc as _EpisodeStoryArc, AgentLongMemory as _AgentLongMemory
from loopforge.stage.stage_episode import (
    StageEpisode,
    StageDay,
    StageAgentDayView,
    StageAgentSummary,
    StageNarrativeBlock,
    StageAgentTraits,
)

# Note on imports:
# - The stage layer depends on analytics and schema (allowed by layering rules).
# - It must not import CLI. It remains pure and JSON-serializable.


def _story_arc_to_mapping(story_arc: Optional[_EpisodeStoryArc]) -> Optional[Mapping[str, Any]]:
    if story_arc is None:
        return None
    # Convert to plain dict to decouple from schema types
    try:
        return story_arc.to_dict()  # type: ignore[attr-defined]
    except Exception:
        # Fail-soft, return a shallow asdict if it's a dataclass; else wrap minimal
        try:
            return asdict(story_arc)  # type: ignore[arg-type]
        except Exception:
            return {"title": getattr(story_arc, "title", None)}


def _long_memory_to_mapping_map(long_memory: Optional[Dict[str, _AgentLongMemory]]) -> Optional[Dict[str, Mapping[str, Any]]]:
    if not long_memory:
        return None
    out: Dict[str, Mapping[str, Any]] = {}
    for name, mem in long_memory.items():
        try:
            out[name] = mem.to_dict()  # type: ignore[attr-defined]
        except Exception:
            try:
                out[name] = asdict(mem)  # type: ignore[arg-type]
            except Exception:
                out[name] = {"confidence": getattr(mem, "confidence", None)}
    return out


def build_stage_episode(
    episode_summary: EpisodeSummary,
    day_summaries: List[DaySummary],
    story_arc: _EpisodeStoryArc | None,
    long_memory: Dict[str, _AgentLongMemory] | None,
    character_defs: Dict[str, Mapping[str, Any]] | None = None,
) -> StageEpisode:
    """Build a StageEpisode with correct structure and placeholder values.

    Sprint 0.1: structure only; minimal field mapping, many placeholders.
    No simulation behavior changes; this is a view-layer assembly.
    """

    # Days
    stage_days: List[StageDay] = []
    for d in day_summaries:
        agents: Dict[str, StageAgentDayView] = {}
        for name, stats in d.agent_stats.items():
            agents[name] = StageAgentDayView(
                name=name,
                role=stats.role,
                avg_stress=stats.avg_stress,
                guardrail_count=stats.guardrail_count,
                context_count=stats.context_count,
                narrative=[],  # placeholder; will be populated in 0.2
            )
        stage_days.append(
            StageDay(
                day_index=d.day_index,
                perception_mode=d.perception_mode,
                tension_score=d.tension_score,
                agents=agents,
                total_incidents=d.total_incidents,
                supervisor_activity=d.supervisor_activity,
                narrative=[],  # placeholder per-day narrative blocks
            )
        )

    # Agents (episode-level)
    stage_agents: Dict[str, StageAgentSummary] = {}
    for name, a in episode_summary.agents.items():
        traits = StageAgentTraits() if a.trait_snapshot else None
        stage_agents[name] = StageAgentSummary(
            name=name,
            role=a.role,
            guardrail_total=a.guardrail_total,
            context_total=a.context_total,
            stress_start=a.stress_start,
            stress_end=a.stress_end,
            trait_snapshot=traits,  # placeholder; 0.2 may map real snapshot
            visual=a.visual,
            vibe=a.vibe,
            tagline=a.tagline,
        )

    # Assemble top-level episode
    stage_ep = StageEpisode(
        episode_id=episode_summary.episode_id,
        run_id=episode_summary.run_id,
        episode_index=episode_summary.episode_index,
        days=stage_days,
        agents=stage_agents,
        story_arc=_story_arc_to_mapping(story_arc),
        narrative=[],  # placeholder episode-level narrative
        long_memory=_long_memory_to_mapping_map(long_memory),
        character_defs=character_defs if character_defs else None,
    )

    return stage_ep
