from __future__ import annotations

"""
Pressure Notes helpers (pure, deterministic, above the seam).

Build short per-agent pressure lines for the episode recap using only telemetry-backed
summaries. No randomness, no side effects.

Inputs:
- EpisodeSummary (for tension trend and agent trait_snapshot)
- DaySummary list (for per-day incidents and supervisor_activity, etc.)

Outputs:
- classify_pressure: a compact phrase capturing the dominant pressure
- summarize_traits: a tiny trait summary using episode-level trait_snapshot
- build_pressure_lines: a list of bullet lines suitable for recap printing
"""
from typing import List, Dict, Optional

from .reporting import EpisodeSummary, DaySummary, AgentEpisodeStats


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _trend_from_tensions(tensions: List[float], eps: float = 0.05) -> str:
    if not tensions:
        return "flat"
    start, end = float(tensions[0]), float(tensions[-1])
    delta = end - start
    if delta > eps:
        return "rising"
    if delta < -eps:
        return "falling"
    return "flat"


def classify_pressure(
    episode: EpisodeSummary,
    day_summaries: List[DaySummary],
    agent_name: str,
) -> str:
    """Return a compact pressure phrase per brief using deterministic rules.

    Uses:
    - total_incidents = sum of incidents_nearby in DaySummary.agent_stats[agent_name]
    - trend from episode.tension_trend (or .tension_values); fallback to day_summaries' tension_score
    - avg_supervisor = mean(day.supervisor_activity) with fallback to 0.0 if missing
    """
    # total incidents for the agent across the episode
    total_incidents = 0
    for d in day_summaries:
        try:
            s = d.agent_stats.get(agent_name)
            if s is not None:
                total_incidents += int(getattr(s, "incidents_nearby", 0) or 0)
        except Exception:
            continue

    # Tension trend
    tensions: List[float] = []
    # Prefer tension_trend if present; some repos may name this tension_values
    try:
        tt = getattr(episode, "tension_trend", None)
        if isinstance(tt, list) and tt:
            tensions = [float(x) for x in tt]
        else:
            tv = getattr(episode, "tension_values", None)
            if isinstance(tv, list) and tv:
                tensions = [float(x) for x in tv]
    except Exception:
        tensions = []
    if not tensions:
        try:
            tensions = [float(getattr(d, "tension_score", 0.0) or 0.0) for d in day_summaries]
        except Exception:
            tensions = []
    trend = _trend_from_tensions(tensions)

    # Average supervisor activity from DaySummary.supervisor_activity (0..1)
    sup_vals: List[float] = []
    for d in day_summaries:
        try:
            sup_vals.append(float(getattr(d, "supervisor_activity", 0.0) or 0.0))
        except Exception:
            sup_vals.append(0.0)
    avg_supervisor = _mean(sup_vals)

    # Deterministic rule table
    if total_incidents > 0 and trend == "rising":
        return "incidents under rising tension"
    if total_incidents > 0 and trend in {"flat", "falling"}:
        return "isolated incidents under mild tension"
    if avg_supervisor > 0.6 and trend == "rising":
        return "tight supervision under rising tension"
    if avg_supervisor < 0.2 and trend == "rising":
        return "rising tension with silent supervisor"
    if avg_supervisor < 0.2 and trend in {"flat", "falling"}:
        return "quiet shift under hands-off supervision"
    return "routine pressure"


def summarize_traits(trait_snapshot: Optional[Dict[str, float]]) -> str:
    """Produce a compact trait summary using arrows vs neutral 0.5 baseline.

    - Neutral band: [0.48, 0.52]
    - Highlights up to 3 items in stable key order
    - Keys considered (if present): agency, trust_supervisor, resilience, caution, variance
    """
    if not trait_snapshot:
        return "traits stable"

    keys = ["agency", "trust_supervisor", "resilience", "caution", "variance"]
    highlights: List[str] = []
    for k in keys:
        if k in trait_snapshot:
            try:
                v = float(trait_snapshot.get(k))
            except Exception:
                continue
            if v > 0.52:
                highlights.append(f"{k}↑")
            elif v < 0.48:
                highlights.append(f"{k}↓")
        if len(highlights) >= 3:
            break

    return ", ".join(highlights) if highlights else "traits stable"


def build_pressure_lines(
    episode: EpisodeSummary,
    day_summaries: List[DaySummary],
) -> List[str]:
    """Build bullet lines for all agents with available names/traits.

    - Agent discovery: union of episode.agents and per-day agent_stats maps
    - Deterministic ordering: alphabetical by agent name
    - Trait snapshot source: AgentEpisodeStats.trait_snapshot (do not invent containers)
    """
    names: Dict[str, bool] = {}
    try:
        for n in (episode.agents or {}).keys():
            names[str(n)] = True
    except Exception:
        pass
    for d in day_summaries:
        try:
            for n in d.agent_stats.keys():
                names[str(n)] = True
        except Exception:
            continue

    lines: List[str] = []
    for name in sorted(names.keys()):
        # trait snapshot from EpisodeSummary.agents[name]
        traits = None
        try:
            agent_stats: AgentEpisodeStats | None = (episode.agents or {}).get(name)  # type: ignore[assignment]
        except Exception:
            agent_stats = None
        if agent_stats is not None:
            try:
                traits = getattr(agent_stats, "trait_snapshot", None)
            except Exception:
                traits = None

        pressure = classify_pressure(episode, day_summaries, name)
        trait_text = summarize_traits(traits)
        lines.append(f"• {name}: {pressure}; {trait_text}.")

    return lines
