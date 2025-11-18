from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Iterable
from collections import Counter

from .types import ActionLogEntry, AgentReflection
from .characters import CHARACTERS
from .types import BeliefState, BeliefAttribution
from .beliefs import derive_belief_state
from .attribution import derive_belief_attribution
from .narrative_reflection import derive_reflection_state
from .emotion_model import derive_emotion_state


@dataclass
class AgentDayStats:
    name: str
    role: str
    guardrail_count: int = 0
    context_count: int = 0
    avg_stress: float = 0.0
    incidents_nearby: int = 0  # placeholder hook; not populated yet
    reflection: Optional[AgentReflection] = None


@dataclass
class DaySummary:
    day_index: int
    perception_mode: str  # "accurate" | "partial" | "spin" (best-effort)
    tension_score: float
    agent_stats: Dict[str, AgentDayStats] = field(default_factory=dict)
    total_incidents: int = 0
    # Sprint 7: Supervisor presence signal (normalized 0..1) — additive, used by views only
    supervisor_activity: float = 0.0
    # Phase 1–2: read-only belief layer per agent (keyed by agent name)
    beliefs: Dict[str, "BeliefState"] = field(default_factory=dict)
    # Sprint 2: Attribution engine outputs per agent (keyed by agent name)
    belief_attributions: Dict[str, "BeliefAttribution"] = field(default_factory=dict)
    # Sprint 3: Reflection state per agent for narrative consistency (keyed by agent name)
    reflection_states: Dict[str, "AgentReflectionState"] = field(default_factory=dict)
    # Sprint 6: Emotional arc engine per agent (keyed by agent name)
    emotion_states: Dict[str, "AgentEmotionState"] = field(default_factory=dict)


@dataclass
class AgentEpisodeStats:
    name: str
    role: str
    guardrail_total: int
    context_total: int
    trait_deltas: Dict[str, float]
    stress_start: Optional[float]
    stress_end: Optional[float]
    representative_reflection: Optional[AgentReflection]
    # Character flavor for reporting (from loopforge.characters)
    visual: str = ""
    vibe: str = ""
    tagline: str = ""
    # Sprint 9: Optional per-episode trait snapshot (deterministic, additive)
    trait_snapshot: Optional[Dict[str, float]] = None


@dataclass
class EpisodeSummary:
    days: List[DaySummary]
    agents: Dict[str, AgentEpisodeStats]
    tension_trend: List[float]
    # Identity fields (Sprint E1/E2) — additive and above-the-seam
    episode_id: Optional[str] = None
    run_id: Optional[str] = None
    episode_index: int = 0
    # Sprint 8: Optional episode-level story arc (deterministic, additive)
    story_arc: Optional["EpisodeStoryArc"] = None
    # Sprint 10: Optional per-agent long memory map (deterministic, additive)
    long_memory: Optional[Dict[str, "AgentLongMemory"]] = None
    # Sprint A0: Optional per-day World Pulse history (deterministic, additive)
    world_pulse_history: Optional[List[Dict[str, float | str]]] = None
    # Sprint S1: Optional Supervisor Weather (deterministic, additive)
    supervisor_weather: Optional["SupervisorEpisodeWeather"] = None


# ------------------------- Helpers -------------------------------------------

def _avg(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def _majority(items: Iterable[str], default: str = "accurate") -> str:
    counts: Dict[str, int] = {}
    for it in items:
        if not it:
            continue
        counts[it] = counts.get(it, 0) + 1
    if not counts:
        return default
    return max(counts, key=counts.get)


def _compute_tension(agent_stats: Dict[str, AgentDayStats], total_incidents: int) -> float:
    """Heuristic tension index: mean stress + 0.5*spread + 0.1*incidents (clamped).

    Consistent trend matters more than exact numbers.
    """
    stresses = [s.avg_stress for s in agent_stats.values()]
    if not stresses:
        return 0.0
    mean_stress = _avg(stresses)
    spread = (max(stresses) - min(stresses)) if len(stresses) > 1 else 0.0
    incident_bump = 0.1 * float(total_incidents)
    val = mean_stress + 0.5 * spread + incident_bump
    if val < 0.0:
        return 0.0
    if val > 1.0:
        return 1.0
    return val


# ------------------------- Public API ----------------------------------------

def summarize_day(
    day_index: int,
    entries: List[ActionLogEntry],
    reflections_by_agent: Optional[Dict[str, AgentReflection]] = None,
    *,
    previous_day_stats: Optional[Dict[str, "AgentDayStats"]] = None,
    supervisor_activity: float = 0.0,
) -> DaySummary:
    """Build a DaySummary from a slice of ActionLogEntry rows.

    - Uses entry.mode for guardrail/context counts.
    - Averages stress from entry.perception["emotions"]["stress"].
    - Best-effort incidents: counts entries where entry.outcome == "incident".
    - Perception mode: majority of perception["perception_mode"], fallback to "accurate".
    - Optionally attaches a reflection per agent.
    """
    reflections_by_agent = reflections_by_agent or {}

    # Group entries by agent
    by_agent: Dict[str, List[ActionLogEntry]] = {}
    for e in entries:
        # Skip empty agent names just in case
        name = getattr(e, "agent_name", None)
        if not name:
            continue
        by_agent.setdefault(name, []).append(e)

    # Build AgentDayStats per agent
    agent_stats: Dict[str, AgentDayStats] = {}
    perception_modes: List[str] = []
    total_incidents = 0

    for name, rows in by_agent.items():
        role = rows[0].role if rows else ""
        guardrail = 0
        context = 0
        stress_vals: List[float] = []
        incidents_for_agent = 0
        for r in rows:
            m = getattr(r, "mode", "guardrail")
            if m == "guardrail":
                guardrail += 1
            elif m == "context":
                context += 1
            # Stress from embedded perception snapshot
            try:
                emo = (r.perception or {}).get("emotions") or {}
                stress_vals.append(float(emo.get("stress", 0.0)))
            except Exception:
                pass
            # Perception mode if present
            try:
                pm = (r.perception or {}).get("perception_mode")
                if isinstance(pm, str) and pm:
                    perception_modes.append(pm)
            except Exception:
                pass
            # Incident indicator (best-effort)
            if (getattr(r, "outcome", None) or "").lower() == "incident":
                total_incidents += 1
                incidents_for_agent += 1
        stats = AgentDayStats(
            name=name,
            role=role,
            guardrail_count=guardrail,
            context_count=context,
            avg_stress=_avg(stress_vals),
            incidents_nearby=incidents_for_agent,
            reflection=reflections_by_agent.get(name),
        )
        agent_stats[name] = stats

    # Perception mode: majority vote across entries (fallback accurate)
    perception_mode = _majority(perception_modes, default="accurate")
    tension = _compute_tension(agent_stats, total_incidents)

    # Phase 1–2: Derive read-only beliefs per agent (no side effects)
    beliefs: Dict[str, BeliefState] = {}
    belief_attributions: Dict[str, BeliefAttribution] = {}
    reflection_states: Dict[str, "AgentReflectionState"] = {}
    prev_map = previous_day_stats or {}
    for name, stats in agent_stats.items():
        prev_stats = prev_map.get(name) if isinstance(prev_map, dict) else None
        try:
            beliefs[name] = derive_belief_state(
                agent_day_stats=stats,
                previous_stats=prev_stats,
                supervisor_activity=float(supervisor_activity or 0.0),
                tension=float(tension or 0.0),
            )
        except Exception:
            # Fail-soft: if derivation fails, skip beliefs for that agent
            pass
        # Attribution derivation (Sprint 2): compute alongside beliefs so CLI path always has data
        try:
            belief_attributions[name] = derive_belief_attribution(
                agent_day_stats=stats,
                previous_stats=prev_stats,
                supervisor_activity=float(supervisor_activity or 0.0),
                tension=float(tension or 0.0),
            )
        except Exception:
            # Fail-soft: keep other outputs intact
            pass
        # Reflection state derivation (Sprint 3): narrative consistency layer
        try:
            reflection_states[name] = derive_reflection_state(
                stats,
                prev_stats,
                float(supervisor_activity or 0.0),
            )
        except Exception:
            # Fail-soft: do not block summary
            pass

    # Sprint 6: Emotional arc engine per agent — derive after we have reflection & attribution
    emotion_states: Dict[str, "AgentEmotionState"] = {}
    for name, stats in agent_stats.items():
        rs = (reflection_states or {}).get(name)
        ba = (belief_attributions or {}).get(name)
        try:
            emotion_states[name] = derive_emotion_state(
                agent_day_stats=stats,
                reflection_state=rs,
                attribution=ba,
            )
        except Exception:
            # Fail-soft: keep other outputs intact
            pass

    # If no entries produced agent stats this day but we have previous_day_stats,
    # still expose reflection state so supervisor_presence can surface in views/tests.
    if not agent_stats and isinstance(prev_map, dict) and prev_map:
        for pname, pstats in prev_map.items():
            try:
                reflection_states[pname] = derive_reflection_state(
                    pstats,  # use previous as current snapshot for narrative-only state
                    pstats,
                    float(supervisor_activity or 0.0),
                )
            except Exception:
                pass

    return DaySummary(
        day_index=day_index,
        perception_mode=perception_mode,
        tension_score=tension,
        agent_stats=agent_stats,
        total_incidents=total_incidents,
        supervisor_activity=float(supervisor_activity or 0.0),
        beliefs=beliefs,
        belief_attributions=belief_attributions,
        reflection_states=reflection_states,
        emotion_states=emotion_states,
    )


def summarize_episode(day_summaries: List[DaySummary], *, previous_long_memory: Optional[Dict[str, "AgentLongMemory"]] = None, episode_id: Optional[str] = None, run_id: Optional[str] = None, episode_index: int = 0) -> EpisodeSummary:
    """Aggregate day summaries into an episode-level view per agent and overall.

    - Totals guardrail/context per agent across days.
    - Captures stress arc start→end per agent using avg_stress from Day 0/last day.
    - Placeholder trait deltas: empty dict (no trait snapshots wired yet).
    - Representative reflection: choose the last non-null reflection seen across days.
    - Enriches AgentEpisodeStats with character flavor (visual/vibe/tagline) from CHARACTERS.
    """
    agents: Dict[str, AgentEpisodeStats] = {}

    # Discover all agent names across days (stable order not required)
    all_agent_names: Dict[str, str] = {}
    for d in day_summaries:
        for name, s in d.agent_stats.items():
            all_agent_names[name] = s.role

    for name, role in all_agent_names.items():
        guardrail_total = 0
        context_total = 0
        stress_start: Optional[float] = None
        stress_end: Optional[float] = None
        rep_reflection: Optional[AgentReflection] = None

        for idx, d in enumerate(day_summaries):
            s = d.agent_stats.get(name)
            if not s:
                continue
            guardrail_total += int(s.guardrail_count)
            context_total += int(s.context_count)
            if idx == 0:
                stress_start = s.avg_stress
            stress_end = s.avg_stress
            if s.reflection is not None:
                rep_reflection = s.reflection

        # Character flavor lookup (safe fallback to empty strings)
        spec = CHARACTERS.get(name, {})
        visual = spec.get("visual", "") if isinstance(spec, dict) else ""
        vibe = spec.get("vibe", "") if isinstance(spec, dict) else ""
        tagline = spec.get("tagline", "") if isinstance(spec, dict) else ""

        agents[name] = AgentEpisodeStats(
            name=name,
            role=role,
            guardrail_total=guardrail_total,
            context_total=context_total,
            trait_deltas={},
            stress_start=stress_start,
            stress_end=stress_end,
            representative_reflection=rep_reflection,
            visual=visual,
            vibe=vibe,
            tagline=tagline,
        )

    tension_trend = [d.tension_score for d in day_summaries]
    summary = EpisodeSummary(days=day_summaries, agents=agents, tension_trend=tension_trend, episode_id=episode_id, run_id=run_id, episode_index=episode_index)

    # Sprint A0: derive per-day World Pulse (fail-soft, additive)
    try:
        if getattr(summary, "world_pulse_history", None) is None:
            from .world_pulse import compute_world_pulse as _compute_world_pulse
            summary.world_pulse_history = [
                _compute_world_pulse(idx) for idx in range(len(day_summaries))
            ]
    except Exception:
        # Leave unset on any failure; views must be resilient to None
        pass

    # Sprint 8: derive optional episode-level story arc (fail-soft)
    try:
        from .story_arc import derive_episode_story_arc
        summary.story_arc = derive_episode_story_arc(summary)
    except Exception:
        # Keep summary.story_arc as None on any failure
        pass

    # Sprint 9: derive and attach trait drift snapshots per agent (fail-soft)
    try:
        from .trait_drift import derive_trait_snapshot
        for name in list(summary.agents.keys()):
            try:
                snap = derive_trait_snapshot(
                    prev_traits=None,  # future: pass persisted previous episode snapshot if available
                    episode_summary=summary,
                    agent_name=name,
                )
                summary.agents[name].trait_snapshot = snap
            except Exception:
                # Do not block episode summarization on per-agent trait computation
                continue
    except Exception:
        # If module import fails, leave snapshots unset
        pass

    # Sprint 10: derive and attach long-memory per agent (fail-soft, additive)
    try:
        from .long_memory import update_long_memory_for_agent
        from .types import AgentLongMemory as _AgentLongMemory
        incidents_in_episode = sum(int(getattr(d, "total_incidents", 0) or 0) for d in day_summaries)
        long_mem: Dict[str, _AgentLongMemory] = {}
        prev_map = previous_long_memory or {}
        CANON = {"supervisor", "self", "system", "random"}
        # Precompute blame timeline per agent from day_summaries
        agent_names = set(summary.agents.keys())
        for d in day_summaries:
            agent_names.update((d.agent_stats or {}).keys())
        for name in sorted(agent_names):
            try:
                # Build blame timeline from days (canonical causes only; unknowns excluded from diversity)
                timeline: List[str] = []
                for d in day_summaries:
                    amap = getattr(d, "belief_attributions", {}) or {}
                    cause = getattr(amap.get(name), "cause", None) if amap else None
                    timeline.append(str(cause) if isinstance(cause, str) else "unknown")
                # Canonical blame_counts
                counts = Counter(c for c in timeline if c in CANON)
                blame_counts = {k: int(counts.get(k, 0)) for k in CANON}
                a = summary.agents.get(name)
                if a is None:
                    # If agent not in aggregates (no stats), skip
                    continue
                prev_mem = prev_map.get(name) if isinstance(prev_map, dict) else None
                lm = update_long_memory_for_agent(
                    prev_mem,
                    name=name,
                    stress_start=float(a.stress_start or 0.0) if a.stress_start is not None else 0.0,
                    stress_end=float(a.stress_end or 0.0) if a.stress_end is not None else 0.0,
                    guardrail_total=int(a.guardrail_total or 0),
                    context_total=int(a.context_total or 0),
                    blame_counts=blame_counts,
                    blame_timeline=timeline,
                    incidents_in_episode=int(incidents_in_episode),
                    story_arc=getattr(summary, "story_arc", None),
                )
                long_mem[name] = lm
            except Exception:
                continue
        summary.long_memory = long_mem or None
    except Exception:
        # Leave long_memory unset on any failure
        pass

    # Sprint S1: Supervisor Weather (fail-soft, additive)
    try:
        from .supervisor_weather import build_supervisor_weather
        summary.supervisor_weather = build_supervisor_weather(summary, day_summaries)
    except Exception:
        summary.supervisor_weather = getattr(summary, "supervisor_weather", None)

    return summary
