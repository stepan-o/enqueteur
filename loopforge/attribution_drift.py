from __future__ import annotations

"""
Attribution & Distortions Feedback Loop (Sprint A1)

Deterministic, additive, above-the-seam builder that fuses attribution signals
with micro-incidents, supervisor weather, emotional carryover, and narrative
pressure into per-agent per-day snapshots and per-episode arcs.

Public API:
- build_attribution_drift(episode: EpisodeSummary, day_summaries: list[DaySummary]) -> AttributionDrift

Notes:
- No randomness; pure arithmetic and template-like score adjustments.
- Fail-soft throughout; missing inputs never raise.
- The function does not mutate inputs; caller may attach the result to
  EpisodeSummary (reporting.summarize_episode does this in a try/except).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .reporting import EpisodeSummary, DaySummary, AgentDayStats

ATTR_CAUSES: Tuple[str, str, str, str] = ("self", "system", "other_agent", "random")


@dataclass(frozen=True)
class AttributionSnapshot:
    day_index: int
    base_cause: Optional[str]
    distorted_cause: str
    distortion_level: float  # 0..1
    drivers: List[str]


@dataclass(frozen=True)
class AgentAttributionArc:
    agent_name: str
    start_cause: str
    end_cause: str
    max_distortion: float
    voice_label: str
    days: List[AttributionSnapshot]


@dataclass(frozen=True)
class AttributionDrift:
    agents: Dict[str, AgentAttributionArc]


# --------------------------- helpers ---------------------------

def _clamp01(x: Optional[float]) -> float:
    try:
        v = float(0.0 if x is None else x)
    except Exception:
        v = 0.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _agent_names_for_day(day: DaySummary) -> List[str]:
    try:
        return sorted((day.agent_stats or {}).keys())
    except Exception:
        return []


def _avg_stress_for_agent(day: DaySummary, name: str) -> float:
    try:
        s: AgentDayStats = (day.agent_stats or {}).get(name)  # type: ignore[assignment]
        if s is None:
            return 0.0
        return _clamp01(getattr(s, "avg_stress", 0.0))
    except Exception:
        return 0.0


def _supervisor_trust(day: DaySummary, name: str) -> Optional[float]:
    try:
        bmap = getattr(day, "beliefs", {}) or {}
        b = bmap.get(name)
        v = getattr(b, "supervisor_trust", None) if b is not None else None
        if v is None and isinstance(b, dict):
            v = b.get("supervisor_trust")
        return None if v is None else _clamp01(float(v))
    except Exception:
        return None


def _base_cause(day: DaySummary, name: str) -> Optional[str]:
    try:
        amap = getattr(day, "belief_attributions", {}) or {}
        obj = amap.get(name)
        cause = getattr(obj, "cause", None) if obj is not None else None
        if cause is None and isinstance(obj, dict):
            cause = obj.get("cause")
        if isinstance(cause, str) and cause:
            # Map any historical label variants
            if cause == "supervisor":
                return "system"  # collapse onto canonical space
            return cause if cause in ATTR_CAUSES else None
    except Exception:
        pass
    return None


def _normalize(scores: Dict[str, float]) -> Dict[str, float]:
    # Ensure all present and non-negative
    for k in ATTR_CAUSES:
        scores[k] = max(0.0, float(scores.get(k, 0.0) or 0.0))
    s = sum(scores.values())
    if s <= 0.0:
        return {k: (1.0 if k == "self" else 0.0) for k in ATTR_CAUSES}
    return {k: (scores[k] / s) for k in ATTR_CAUSES}


def _argmax(scores: Dict[str, float]) -> str:
    best_k = "self"
    best_v = -1.0
    for k in ATTR_CAUSES:
        v = float(scores.get(k, 0.0) or 0.0)
        if v > best_v or (v == best_v and k < best_k):
            best_v = v
            best_k = k
    return best_k


def _voice_label_for_arc(start_cause: str, end_cause: str, max_distortion: float) -> str:
    md = _clamp01(max_distortion)
    if end_cause == "self" and md >= 0.3:
        return "self-blaming"
    if end_cause in {"system", "other_agent"} and md >= 0.25:
        return "paranoid" if end_cause == "system" else "externalizing"
    if end_cause == "random" and md >= 0.25:
        return "fatalistic"
    if end_cause == "self" and md < 0.2:
        return "stable/grounded"
    return "mixed"


# --------------------------- main builder ---------------------------

def build_attribution_drift(
    episode: EpisodeSummary,
    day_summaries: List[DaySummary],
) -> AttributionDrift:
    """Build deterministic attribution drift across an episode.

    Pipeline summary:
    - Seed base cause rails from explicit attributions or previous day carryover.
    - Apply emotional carryover (stress + trust) as arithmetic shifts.
    - Fold in micro-incidents per (day,agent) by type/severity mapping.
    - Reinforce with Supervisor Weather (targets + punitive/global pressure cues).
    - Add narrative bias from tension trend and (optional) story arc direction.
    - Normalize, pick distorted cause, compute distortion level, collect drivers.
    - Aggregate snapshots per agent to arcs + voice labels.
    """
    # Precompute micro-incidents once (fail-soft)
    incidents_by_day_agent: Dict[Tuple[int, str], List[object]] = {}
    try:
        from .micro_incidents import build_micro_incidents  # local import to avoid cycles
        inc_list = build_micro_incidents(episode) or []
        for mi in inc_list:
            try:
                key_agents = list(getattr(mi, "agents_involved", []) or [])
                day_idx = int(getattr(mi, "day_index", 0) or 0)
                if not key_agents:
                    # Assign to a generic bucket; handled by applying to top agent later
                    key = (day_idx, "*")
                    incidents_by_day_agent.setdefault(key, []).append(mi)
                else:
                    for name in key_agents:
                        key = (day_idx, str(name))
                        incidents_by_day_agent.setdefault(key, []).append(mi)
            except Exception:
                continue
    except Exception:
        incidents_by_day_agent = {}

    # Supervisor weather index (fail-soft)
    sw_by_day: Dict[int, object] = {}
    try:
        sw = getattr(episode, "supervisor_weather", None)
        for d in (getattr(sw, "days", []) or []):
            idx = int(getattr(d, "day_index", 0) or 0)
            sw_by_day[idx] = d
    except Exception:
        sw_by_day = {}

    # Tension trend orientation
    trend_bias = 0.0
    try:
        tt = list(getattr(episode, "tension_trend", []) or [])
        if tt:
            delta = float(tt[-1]) - float(tt[0])
            if delta > 0.05:
                trend_bias = +1.0  # rising → world feels harsher
            elif delta < -0.05:
                trend_bias = -1.0  # easing
    except Exception:
        trend_bias = 0.0

    # Optional story arc polarity
    arc_bias = 0.0
    try:
        arc = getattr(episode, "story_arc", None)
        # Very light heuristic: arc_type in {decompression, escalation, back_and_forth, flatline, uncertain}
        arc_type = getattr(arc, "arc_type", None)
        if arc_type in {"escalation", "back_and_forth"}:
            arc_bias = +0.5
        elif arc_type in {"decompression"}:
            arc_bias = -0.5
    except Exception:
        arc_bias = 0.0

    # Collect snapshots per agent
    by_agent_snaps: Dict[str, List[AttributionSnapshot]] = {}
    prev_distorted: Dict[str, str] = {}

    for day in day_summaries:
        day_index = int(getattr(day, "day_index", 0) or 0)
        names = _agent_names_for_day(day)
        for name in names:
            drivers: List[str] = []
            # Step 1: seed base rails
            base = _base_cause(day, name)
            if base is None:
                base = prev_distorted.get(name, None)
            scores: Dict[str, float] = {k: 0.0 for k in ATTR_CAUSES}
            if base in ATTR_CAUSES:
                scores[base] += 0.7
            else:
                # Default low-rail to self
                scores["self"] += 0.5

            # Step 2: emotional carryover (stress & trust)
            stress = _avg_stress_for_agent(day, name)
            trust = _supervisor_trust(day, name)
            # Push away from self under stress + low trust
            scores["system"] += stress * (1.0 - (trust if trust is not None else 0.5))
            scores["self"] += (1.0 - stress) * ((trust if trust is not None else 0.5) * 0.5)
            # Under very low stress, allow some randomness/forgiveness
            if stress < 0.15 and (trust or 0.5) > 0.6:
                scores["random"] += 0.05

            # Step 3: micro-incidents (type+severity mapping)
            try:
                relevant: List[object] = []
                relevant.extend(incidents_by_day_agent.get((day_index, name), []))
                relevant.extend(incidents_by_day_agent.get((day_index, "*"), []))
                if relevant:
                    if "micro_incident" not in drivers:
                        drivers.append("micro_incident")
                for mi in relevant:
                    itype = getattr(mi, "incident_type", None)
                    sev = str(getattr(mi, "severity", "low") or "low").lower()
                    bump = 0.1 if sev == "low" else (0.2 if sev == "medium" else 0.3)
                    if itype == "glitch":
                        scores["system"] += bump
                    elif itype == "friction":
                        scores["other_agent"] += bump
                    elif itype == "tension_spike":
                        # Amplify current top non-self
                        top = _argmax(scores)
                        target = top if top != "self" else "system"
                        scores[target] += bump
                    elif itype == "weirdness":
                        scores["random"] += bump
                        scores["system"] += bump * 0.3
            except Exception:
                pass

            # Step 4: supervisor weather reinforcement
            try:
                swd = sw_by_day.get(day_index)
                if swd is not None:
                    # Global bias under punitive mood + high pressure
                    mood = getattr(swd, "mood", None)
                    gpressure = getattr(swd, "global_pressure", None)
                    if mood == "punitive" and gpressure == "high":
                        scores["system"] += 0.1
                        scores["random"] = max(0.0, scores.get("random", 0.0) - 0.05)
                    # Per-agent targets
                    for t in (getattr(swd, "targets", []) or []):
                        if getattr(t, "agent_name", None) != name:
                            continue
                        level = getattr(t, "pressure_level", "none")
                        if level in {"firm", "hard"}:
                            if trust is not None and trust >= 0.6:
                                scores["self"] += 0.2 if level == "hard" else 0.1
                            else:
                                scores["system"] += 0.2 if level == "hard" else 0.1
                            if "supervisor_pressure" not in drivers:
                                drivers.append("supervisor_pressure")
            except Exception:
                pass

            # Step 5: narrative pressure (trend + arc)
            try:
                if trend_bias > 0:
                    scores["system"] += 0.05
                    scores["random"] += 0.03
                elif trend_bias < 0:
                    scores["self"] += 0.05
                    scores["other_agent"] += 0.02
                if arc_bias != 0.0:
                    if arc_bias > 0:
                        scores["system"] += 0.03
                    else:
                        scores["self"] += 0.03
                if arc_bias != 0.0 or trend_bias != 0.0:
                    if "narrative" not in drivers:
                        drivers.append("narrative")
            except Exception:
                pass

            # Step 6: normalize & choose distorted cause
            scores = _normalize(scores)
            distorted = _argmax(scores)
            top_score = float(scores.get(distorted, 0.0))
            base_score = float(scores.get(base, 0.0)) if base in ATTR_CAUSES else 0.0
            distortion_level = _clamp01(top_score - base_score) if base is not None else _clamp01(top_score)

            snap = AttributionSnapshot(
                day_index=day_index,
                base_cause=base,
                distorted_cause=distorted,
                distortion_level=distortion_level,
                drivers=drivers,
            )
            by_agent_snaps.setdefault(name, []).append(snap)
            prev_distorted[name] = distorted

    # Step 7: aggregate per-agent arcs
    agents_out: Dict[str, AgentAttributionArc] = {}
    for name in sorted(by_agent_snaps.keys()):
        snaps = by_agent_snaps[name]
        if not snaps:
            continue
        start = snaps[0].distorted_cause
        end = snaps[-1].distorted_cause
        maxd = max((s.distortion_level for s in snaps), default=0.0)
        voice = _voice_label_for_arc(start, end, maxd)
        agents_out[name] = AgentAttributionArc(
            agent_name=name,
            start_cause=start,
            end_cause=end,
            max_distortion=maxd,
            voice_label=voice,
            days=snaps,
        )

    return AttributionDrift(agents=agents_out)
