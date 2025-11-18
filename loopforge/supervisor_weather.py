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
from .reporting import EpisodeSummary, DaySummary, AgentDayStats


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


def _tone_volatility(idx: int, days: List[DaySummary]) -> str:
    # Day-to-day delta of tension and swing in supervisor_activity
    if idx <= 0:
        return "stable"
    curr = days[idx]
    prev = days[idx - 1]
    try:
        d_tension = abs(_clamp01(getattr(curr, "tension_score", 0.0)) - _clamp01(getattr(prev, "tension_score", 0.0)))
    except Exception:
        d_tension = 0.0
    try:
        d_sup = abs(_clamp01(getattr(curr, "supervisor_activity", 0.0)) - _clamp01(getattr(prev, "supervisor_activity", 0.0)))
    except Exception:
        d_sup = 0.0
    if d_tension > TENSION_SPIKE or d_sup > SUPERVISOR_SPIKE:
        return "spiky"
    if d_tension > 0.05 and d_sup > 0.10:
        return "variable"
    return "stable"


def _attrib_drift_penalty(day: DaySummary, name: str) -> float:
    """Penalty based on attribution drifting away from 'self' toward 'system'/'random'."""
    try:
        amap = getattr(day, "belief_attributions", {}) or {}
        obj = amap.get(name)
        cause = getattr(obj, "cause", None) if obj is not None else None
        if isinstance(cause, str):
            if cause == "self":
                return 0.0
            if cause in {"system", "random", "supervisor"}:
                return 1.0
    except Exception:
        pass
    return 0.5  # unknown → medium penalty


def _supervisor_trust(day: DaySummary, name: str) -> Optional[float]:
    try:
        beliefs = getattr(day, "beliefs", {}) or {}
        b = beliefs.get(name)
        v = getattr(b, "supervisor_trust", None) if b is not None else None
        if v is None and isinstance(b, dict):
            v = b.get("supervisor_trust")
        return None if v is None else _clamp01(float(v))
    except Exception:
        return None


def _misalignment_for_agent(day: DaySummary, name: str) -> Tuple[float, str]:
    stats = (getattr(day, "agent_stats", {}) or {}).get(name)
    if stats is None:
        return (0.0, "no data")
    stress = _clamp01(getattr(stats, "avg_stress", 0.0))
    g_ratio = _guardrail_ratio(stats)
    trust = _supervisor_trust(day, name)
    trust_term = (1.0 - _clamp01(trust)) if trust is not None else 0.5
    attrib_pen = _attrib_drift_penalty(day, name)
    score = (
        W_STRESS * stress +
        W_GUARDRAIL * _clamp01(g_ratio) +
        W_LOW_TRUST * trust_term +
        W_ATTRIB_DRIFT * _clamp01(attrib_pen)
    )
    score = _clamp01(score)
    # Reason strings (deterministic buckets)
    reasons: List[str] = []
    if stress >= 0.6:
        reasons.append("stress high")
    if (trust is not None and trust <= 0.4):
        reasons.append("trust low")
    if g_ratio >= 0.7:
        reasons.append("heavy guardrail use")
    if attrib_pen >= 0.9:
        reasons.append("blame off self")
    if not reasons:
        reasons.append("signals mixed")
    reason = ", ".join(reasons)
    return score, reason


def _pressure_level(score: float) -> str:
    if score < 0.25:
        return "none"
    if score < 0.45:
        return "soft"
    if score < 0.70:
        return "firm"
    return "hard"


def _day_alignment_score(misalign_scores: List[float]) -> float:
    return _clamp01(1.0 - _avg([_clamp01(x) for x in misalign_scores]))


def _day_mood(global_pressure: str, alignment: float, targets: List[SupervisorPressureTarget]) -> str:
    hard_count = sum(1 for t in targets if t.pressure_level == "hard")
    if global_pressure == "low" and alignment >= ALIGN_HIGH:
        return "calm"
    if global_pressure == "medium":
        return "focused"
    # high pressure cases
    if global_pressure == "high" and (alignment <= ALIGN_LOW or hard_count >= 1):
        return "punitive" if hard_count >= 1 else "irritated"
    # fallback
    return "irritated" if global_pressure == "high" else "focused"


def _episode_mood_baseline(days: List[SupervisorDayWeather]) -> str:
    # Map bands to numeric for averaging
    band_val = {"low": 0.0, "medium": 0.5, "high": 1.0}
    pressure_vals = [band_val.get(d.global_pressure, 0.5) for d in days]
    avg_pressure = _avg(pressure_vals)
    avg_align = _avg([_clamp01(d.alignment_score) for d in days])
    if avg_pressure <= 0.20 and avg_align >= 0.70:
        return "calm"
    if avg_pressure >= 0.66 and avg_align <= 0.50:
        return "irritated"
    if avg_pressure >= 0.66 and avg_align <= 0.35:
        return "punitive"
    return "focused"


def _episode_mood_trend(days: List[SupervisorDayWeather]) -> str:
    if len(days) < 2:
        return "steady"
    first = days[0]
    last = days[-1]
    band_val = {"low": 0.0, "medium": 0.5, "high": 1.0}
    dp = band_val.get(last.global_pressure, 0.5) - band_val.get(first.global_pressure, 0.5)
    da = _clamp01(last.alignment_score) - _clamp01(first.alignment_score)
    if dp > 0.05 and da < -0.05:
        return "souring"
    if dp < -0.05 and da > 0.05:
        return "improving"
    return "steady"


# ------------------------ Public API ------------------------

def build_supervisor_weather(
    episode: EpisodeSummary,
    day_summaries: List[DaySummary],
) -> SupervisorEpisodeWeather:
    """Compute Supervisor weather deterministically for an episode.

    - Per-day: pressure band, tone volatility, alignment, targets, mood
    - Episode-level mood baseline + trend
    """
    days_out: List[SupervisorDayWeather] = []

    for idx, day in enumerate(day_summaries):
        band, _scalar = _global_pressure_band(day)
        tone_vol = _tone_volatility(idx, day_summaries)
        # Misalignment per agent
        names = sorted((getattr(day, "agent_stats", {}) or {}).keys())
        scores: List[float] = []
        targets: List[SupervisorPressureTarget] = []
        for name in names:
            score, reason_bits = _misalignment_for_agent(day, name)
            scores.append(score)
            level = _pressure_level(score)
            if level != "none":
                # Deterministic phrasing
                reason = (
                    "stress high, trust low — misaligned with guardrail usage"
                    if (score >= 0.7)
                    else (
                        "relying heavily on guardrails despite stable conditions"
                        if (level == "firm")
                        else (
                            "belief drift away from Supervisor under rising tension"
                            if (band == "high")
                            else reason_bits
                        )
                    )
                )
                targets.append(
                    SupervisorPressureTarget(
                        agent_name=name,
                        pressure_level=level,
                        reason=reason,
                        misalignment_score=score,
                    )
                )
        align = _day_alignment_score(scores) if scores else 1.0
        mood = _day_mood(band, align, targets)
        days_out.append(
            SupervisorDayWeather(
                day_index=int(getattr(day, "day_index", idx) or idx),
                mood=mood,
                tone_volatility=tone_vol,
                global_pressure=band,
                alignment_score=align,
                targets=targets,
            )
        )

    mood_baseline = _episode_mood_baseline(days_out)
    mood_trend = _episode_mood_trend(days_out)

    return SupervisorEpisodeWeather(
        mood_baseline=mood_baseline,
        mood_trend=mood_trend,
        days=days_out,
    )
