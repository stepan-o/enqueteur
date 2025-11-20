from __future__ import annotations

"""
Supervisor Weather Engine v2 (Sprint S1)

Deterministic, additive, above-the-seam synthesis of per-day Supervisor
"weather" plus an episode-level summary. Consumes EpisodeSummary/DaySummary
telemetry; does not modify simulation mechanics or log schemas.

Public API:
- build_supervisor_weather(episode: EpisodeSummary, day_summaries: list[DaySummary])

Notes:
- No randomness; pure arithmetic and thresholds.
- Fail-soft to keep callers resilient to missing substructures.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

# Local imports are type-only to avoid import cycles at module import time.
# Concrete types are only used for annotations and runtime attributes access.
from loopforge.analytics.reporting import EpisodeSummary, DaySummary, AgentDayStats


# ------------------------ Data classes ------------------------

@dataclass(frozen=True)
class SupervisorPressureTarget:
    agent_name: str
    pressure_level: str      # "none" | "soft" | "firm" | "hard"
    reason: str              # short, deterministic explanation
    misalignment_score: float  # 0..1


@dataclass(frozen=True)
class SupervisorDayWeather:
    day_index: int
    mood: str                # "calm" | "focused" | "irritated" | "punitive"
    tone_volatility: str     # "stable" | "variable" | "spiky"
    global_pressure: str     # "low" | "medium" | "high"
    alignment_score: float   # 0..1
    targets: List[SupervisorPressureTarget]


@dataclass(frozen=True)
class SupervisorEpisodeWeather:
    mood_baseline: str        # overall episode mood
    mood_trend: str           # "steady" | "souring" | "improving"
    days: List[SupervisorDayWeather]


# ------------------------ Tunable thresholds ------------------------

# Global pressure band thresholds (based on scalar in [0,1])
PRESSURE_LOW_MAX = 0.15
PRESSURE_MED_MAX = 0.35  # (low, MED] then > MED => high

# Tone volatility thresholds
TENSION_SPIKE = 0.20  # |delta tension| > 0.2 => spiky
SUPERVISOR_SPIKE = 0.50  # big jump in activity (normalized 0..1)

# Misalignment weights
W_STRESS = 0.40
W_GUARDRAIL = 0.25
W_LOW_TRUST = 0.25
W_ATTRIB_DRIFT = 0.10

# Supervisor mood mapping weights
# Mood decided from (pressure band, alignment, hard-target count)
ALIGN_HIGH = 0.75
ALIGN_LOW = 0.40


# ------------------------ Helpers ------------------------

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


def _avg(xs: List[float]) -> float:
    return (sum(xs) / len(xs)) if xs else 0.0


def _guardrail_ratio(stats: AgentDayStats) -> float:
    g = float(getattr(stats, "guardrail_count", 0) or 0)
    c = float(getattr(stats, "context_count", 0) or 0)
    tot = g + c
    return 1.0 if tot <= 0 else g / tot


def _context_ratio(stats: AgentDayStats) -> float:
    g = float(getattr(stats, "guardrail_count", 0) or 0)
    c = float(getattr(stats, "context_count", 0) or 0)
    tot = g + c
    return 0.0 if tot <= 0 else c / tot


def _global_pressure_band(day: DaySummary) -> Tuple[str, float]:
    tension = _clamp01(getattr(day, "tension_score", 0.0))
    avg_st = _avg([_clamp01(getattr(s, "avg_stress", 0.0)) for s in (getattr(day, "agent_stats", {}) or {}).values()])
    scalar = _clamp01(0.5 * tension + 0.5 * avg_st)
    if scalar <= PRESSURE_LOW_MAX:
        return ("low", scalar)
    if scalar <= PRESSURE_MED_MAX:
        return ("medium", scalar)
    return ("high", scalar)


def _tone_volatility(day_prev: Optional[DaySummary], day: DaySummary) -> str:
    try:
        tprev = _clamp01(getattr(day_prev, "tension_score", 0.0)) if day_prev is not None else None
        tcur = _clamp01(getattr(day, "tension_score", 0.0))
        sup_prev = float(getattr(day_prev, "supervisor_activity", 0.0)) if day_prev is not None else None
        sup_cur = float(getattr(day, "supervisor_activity", 0.0))
    except Exception:
        return "stable"
    spike = False
    if tprev is not None and abs(tcur - tprev) > TENSION_SPIKE:
        spike = True
    if sup_prev is not None and abs(sup_cur - sup_prev) > SUPERVISOR_SPIKE:
        spike = True
    return "spiky" if spike else ("variable" if (tprev is not None and tprev != tcur) else "stable")


def _misalignment_score(day: DaySummary) -> float:
    try:
        # Weighted blend of stress, guardrail skew, low trust, and attribution drift presence
        avg_st = _avg([_clamp01(getattr(s, "avg_stress", 0.0)) for s in (getattr(day, "agent_stats", {}) or {}).values()])
        guard_skew = 0.0
        for s in (getattr(day, "agent_stats", {}) or {}).values():
            try:
                gr = _guardrail_ratio(s)
                guard_skew += abs(0.5 - gr)  # deviation from balance
            except Exception:
                continue
        guard_skew = guard_skew / max(1, len((getattr(day, "agent_stats", {}) or {})))
        low_trust = 0.0
        try:
            beliefs = getattr(day, "beliefs", {}) or {}
            vals = []
            for b in beliefs.values():
                try:
                    vals.append(1.0 - _clamp01(getattr(b, "supervisor_trust", 0.5)))
                except Exception:
                    continue
            low_trust = _avg(vals)
        except Exception:
            low_trust = 0.0
        # attribution drift presence proxy
        drift_present = 1.0 if getattr(day, "belief_attributions", {}) else 0.0
        score = (W_STRESS * avg_st) + (W_GUARDRAIL * guard_skew) + (W_LOW_TRUST * low_trust) + (W_ATTRIB_DRIFT * drift_present)
        return _clamp01(score)
    except Exception:
        return 0.0


def build_supervisor_weather(episode: EpisodeSummary, day_summaries: List[DaySummary]) -> SupervisorEpisodeWeather:
    days_out: List[SupervisorDayWeather] = []
    prev: Optional[DaySummary] = None
    for d in day_summaries:
        band, scalar = _global_pressure_band(d)
        vol = _tone_volatility(prev, d)
        align = _clamp01(1.0 - _misalignment_score(d))
        # Day mood mapping
        if band == "high" and align < ALIGN_LOW:
            mood = "punitive"
        elif band == "low" and align >= ALIGN_HIGH:
            mood = "calm"
        elif band == "medium" and align >= ALIGN_HIGH:
            mood = "focused"
        else:
            mood = "irritated" if band != "low" else "focused"
        # Per-agent targets (deterministic): pick agents with highest misalignment components
        targets: List[SupervisorPressureTarget] = []
        try:
            # Use guardrail skew + low_trust as signals to select top 1–2 agents
            stats: Dict[str, AgentDayStats] = getattr(d, "agent_stats", {}) or {}
            beliefs = getattr(d, "beliefs", {}) or {}
            ranking: List[Tuple[str, float]] = []
            for name, s in stats.items():
                try:
                    gr_skew = abs(0.5 - _guardrail_ratio(s))
                except Exception:
                    gr_skew = 0.0
                try:
                    b = beliefs.get(name)
                    lt = (1.0 - _clamp01(getattr(b, "supervisor_trust", 0.5))) if b is not None else 0.5
                except Exception:
                    lt = 0.5
                ranking.append((name, 0.6 * gr_skew + 0.4 * lt))
            ranking.sort(key=lambda t: (-t[1], t[0]))
            top = [r[0] for r in ranking[:2]]
            for i, name in enumerate(top):
                level = "hard" if (band == "high" and align < ALIGN_LOW and i == 0) else ("firm" if band != "low" else "soft")
                reason = "guardrail skew + low trust" if band != "low" else "mild course correction"
                targets.append(SupervisorPressureTarget(agent_name=name, pressure_level=level, reason=reason, misalignment_score=ranking[i][1]))
        except Exception:
            targets = []
        days_out.append(
            SupervisorDayWeather(
                day_index=int(getattr(d, "day_index", 0) or 0),
                mood=mood,
                tone_volatility=vol,
                global_pressure=band,
                alignment_score=align,
                targets=targets,
            )
        )
        prev = d

    # Episode mood baseline/trend
    if not days_out:
        return SupervisorEpisodeWeather(mood_baseline="calm", mood_trend="steady", days=[])
    moods = [x.mood for x in days_out]
    # Simple baseline: majority mood, tie-breaker by severity ordering
    order = {"calm": 0, "focused": 1, "irritated": 2, "punitive": 3}
    from collections import Counter

    cnt = Counter(moods)
    baseline = sorted(cnt.items(), key=lambda kv: (-kv[1], -order.get(kv[0], 0), kv[0]))[0][0]
    # Trend: compare first/last global pressure
    first = order.get(days_out[0].global_pressure, 0)
    last = order.get(days_out[-1].global_pressure, 0)
    if last > first:
        trend = "souring"
    elif last < first:
        trend = "improving"
    else:
        trend = "steady"
    return SupervisorEpisodeWeather(mood_baseline=baseline, mood_trend=trend, days=days_out)
