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
from loopforge.narrative.narrative_viewer import build_day_narrative
from loopforge.narrative.episode_recaps import build_episode_recap

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
    *,
    include_narrative: bool = False,
) -> StageEpisode:
    """Build a StageEpisode from real analytics + narrative sources (Sprint 0.2).

    - Pure mapping; no side effects, no CLI dependencies.
    - Keeps behavior deterministic and JSON-safe.
    """

    # Days with per-agent views and narrative beats
    stage_days: List[StageDay] = []
    prev_day: Optional[DaySummary] = None
    for d in day_summaries:
        agents: Dict[str, StageAgentDayView] = {}
        # Optional overlays available on DaySummary
        emo_map = getattr(d, "emotion_states", {}) or {}
        attr_map = getattr(d, "belief_attributions", {}) or {}

        # Build base per-agent views
        for name, stats in d.agent_stats.items():
            # Emotion state minimal projection
            emo = getattr(emo_map.get(name), "to_dict", None)
            emotional_read: Optional[Mapping[str, Any]] = None
            if callable(emo):
                try:
                    emotional_read = emo_map[name].to_dict()  # type: ignore[assignment]
                except Exception:
                    emotional_read = None
            # Attribution cause (single keyword string), if available
            cause = None
            try:
                aobj = attr_map.get(name)
                cause = getattr(aobj, "cause", None)
            except Exception:
                cause = None

            agents[name] = StageAgentDayView(
                name=name,
                role=stats.role,
                avg_stress=stats.avg_stress,
                guardrail_count=stats.guardrail_count,
                context_count=stats.context_count,
                emotional_read=emotional_read,
                attribution_cause=cause if isinstance(cause, str) else None,
                narrative=[],
            )

        # Day-level narrative integration (optional)
        day_blocks: List[StageNarrativeBlock] = []
        if include_narrative:
            try:
                dn = build_day_narrative(d, d.day_index, previous_day_summary=prev_day)
                # Attach agent-specific beats to their views (short joined lines)
                for beat in getattr(dn, "agent_beats", []) or []:
                    text = " ".join([x for x in [beat.intro, beat.perception_line, beat.actions_line, beat.closing_line] if isinstance(x, str)])
                    block = StageNarrativeBlock(
                        block_id=None,
                        kind="beat",
                        text=text,
                        day_index=d.day_index,
                        agent_name=beat.name,
                        tags=["agent_beat"],
                    )
                    if beat.name in agents:
                        agents[beat.name].narrative.append(block)
                # Day-level intro/supervisor/outro blocks
                if getattr(dn, "day_intro", None):
                    day_blocks.append(StageNarrativeBlock(kind="day_intro", text=dn.day_intro, day_index=d.day_index))
                if getattr(dn, "supervisor_line", None):
                    day_blocks.append(StageNarrativeBlock(kind="supervisor", text=dn.supervisor_line, day_index=d.day_index))
                if getattr(dn, "day_outro", None):
                    day_blocks.append(StageNarrativeBlock(kind="day_outro", text=dn.day_outro, day_index=d.day_index))
            except Exception:
                day_blocks = []

        stage_days.append(
            StageDay(
                day_index=d.day_index,
                perception_mode=d.perception_mode,
                tension_score=d.tension_score,
                agents=agents,
                total_incidents=d.total_incidents,
                supervisor_activity=d.supervisor_activity,
                narrative=day_blocks,
            )
        )
        prev_day = d

    # Agents (episode-level)
    stage_agents: Dict[str, StageAgentSummary] = {}
    for name, a in episode_summary.agents.items():
        traits = StageAgentTraits(**a.trait_snapshot) if isinstance(getattr(a, "trait_snapshot", None), dict) else None
        stage_agents[name] = StageAgentSummary(
            name=name,
            role=a.role,
            guardrail_total=a.guardrail_total,
            context_total=a.context_total,
            stress_start=a.stress_start,
            stress_end=a.stress_end,
            trait_snapshot=traits,
            visual=a.visual,
            vibe=a.vibe,
            tagline=a.tagline,
        )

    # Episode-level narrative recap (optional)
    episode_narrative: List[StageNarrativeBlock] = []
    if include_narrative:
        try:
            recap_chars: Dict[str, Mapping[str, Any]] = character_defs or {}
            recap = build_episode_recap(episode_summary, day_summaries, recap_chars)
            if getattr(recap, "intro", None):
                episode_narrative.append(StageNarrativeBlock(kind="recap_intro", text=recap.intro))
            # Per-agent blurbs as separate blocks
            try:
                for agent_name, blurb in (getattr(recap, "per_agent_blurbs", {}) or {}).items():
                    episode_narrative.append(StageNarrativeBlock(kind="recap_agent", text=blurb, agent_name=agent_name))
            except Exception:
                pass
            if getattr(recap, "closing", None):
                episode_narrative.append(StageNarrativeBlock(kind="recap_closing", text=recap.closing))
            # Optional arc/world pulse/memory/distortion blocks preserved as multi-line text
            for kind_name in [
                ("story_arc_lines", "recap_story_arc"),
                ("world_pulse_lines", "recap_world_pulse"),
                ("micro_incident_lines", "recap_micro_incidents"),
                ("pressure_lines", "recap_pressure"),
            ]:
                key, kind_alias = kind_name
                lines = getattr(recap, key, None)
                if isinstance(lines, list) and lines:
                    episode_narrative.append(
                        StageNarrativeBlock(kind=kind_alias, text="\n".join([str(x) for x in lines]))
                    )
            arc_cohesion = getattr(recap, "arc_cohesion", None)
            if isinstance(arc_cohesion, str) and arc_cohesion:
                episode_narrative.append(StageNarrativeBlock(kind="recap_arc_cohesion", text=arc_cohesion))
            memory_line = getattr(recap, "memory_line", None)
            if isinstance(memory_line, str) and memory_line:
                episode_narrative.append(StageNarrativeBlock(kind="recap_memory_line", text=memory_line))
        except Exception:
            episode_narrative = []

    # Assemble top-level episode
    stage_ep = StageEpisode(
        episode_id=episode_summary.episode_id,
        run_id=episode_summary.run_id,
        episode_index=episode_summary.episode_index,
        tension_trend=list(episode_summary.tension_trend or []),
        days=stage_days,
        agents=stage_agents,
        story_arc=_story_arc_to_mapping(story_arc),
        narrative=episode_narrative,
        long_memory=_long_memory_to_mapping_map(long_memory),
        character_defs=character_defs if character_defs else None,
    )

    return stage_ep
