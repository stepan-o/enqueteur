from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Iterable

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


@dataclass
class EpisodeSummary:
    days: List[DaySummary]
    agents: Dict[str, AgentEpisodeStats]
    tension_trend: List[float]


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
        beliefs=beliefs,
        belief_attributions=belief_attributions,
        reflection_states=reflection_states,
        emotion_states=emotion_states,
    )


def summarize_episode(day_summaries: List[DaySummary]) -> EpisodeSummary:
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
    return EpisodeSummary(days=day_summaries, agents=agents, tension_trend=tension_trend)
