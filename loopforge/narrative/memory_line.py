from __future__ import annotations

"""
Sprint 5 — Memory Line helpers (pure, deterministic, above the seam).

- No randomness, no side effects.
- Consumes only existing telemetry already surfaced in summaries:
  * EpisodeSummary.tension_trend (or fallback to day.tension_score)
  * Per-agent incidents via DaySummary.agent_stats[...].incidents_nearby
  * DaySummary.supervisor_activity (0..1)
  * Reflection tone (from Sprint 4) provided by caller as a string

Public helpers:
- compute_episode_intensity(episode, day_summaries) -> "quiet" | "charged" | "uneasy" | "oversupervised"
- build_memory_line(episode, day_summaries, reflection_tone) -> "Memory Line: <text>."
"""
from typing import List

from loopforge.reporting import EpisodeSummary, DaySummary


_DEF_EPS = 0.05


def _trend_from_tensions(tensions: List[float], eps: float = _DEF_EPS) -> str:
    if not tensions:
        return "flat"
    start, end = float(tensions[0]), float(tensions[-1])
    delta = end - start
    if delta > eps:
        return "rising"
    if delta < -eps:
        return "falling"
    return "flat"


def _mean(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def compute_episode_intensity(episode: EpisodeSummary, day_summaries: List[DaySummary]) -> str:
    """Classify episode "intensity" deterministically using only surfaced telemetry.

    Returns one of: "quiet", "charged", "uneasy", "oversupervised".
    """
    # Sum incidents across all agents/days
    total_incidents = 0
    for d in day_summaries:
        try:
            for s in d.agent_stats.values():
                total_incidents += int(getattr(s, "incidents_nearby", 0) or 0)
        except Exception:
            continue

    # Tension trend from episode.tension_trend (fallback to per-day tension_score)
    tensions: List[float] = []
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

    # Average supervisor activity
    sup_vals: List[float] = []
    for d in day_summaries:
        try:
            sup_vals.append(float(getattr(d, "supervisor_activity", 0.0) or 0.0))
        except Exception:
            sup_vals.append(0.0)
    avg_sup = _mean(sup_vals)

    # Deterministic rule table
    # High supervision dominates regardless of incidents when very high.
    if avg_sup > 0.6 and trend in {"rising", "flat"} and total_incidents == 0:
        return "oversupervised"

    if trend == "rising":
        if total_incidents > 0:
            return "charged"
        if avg_sup > 0.6:
            return "oversupervised"
        return "uneasy"

    if trend == "falling":
        if total_incidents == 0:
            return "quiet"
        if avg_sup > 0.6:
            return "oversupervised"
        return "uneasy"

    # flat trend
    if avg_sup > 0.6:
        return "oversupervised"
    if total_incidents > 0:
        return "uneasy" if avg_sup < 0.2 else "charged"
    return "quiet"


def build_memory_line(
    episode: EpisodeSummary,
    day_summaries: List[DaySummary],
    reflection_tone: str,
) -> str:
    """Build the final Memory Line as a single deterministic sentence.

    reflection_tone: "calming" | "tense" | "mixed"
    """
    intensity = compute_episode_intensity(episode, day_summaries)
    tone = str(reflection_tone or "mixed")

    # Deterministic mapping from (intensity, tone) -> text fragment
    # Keep phrases compact and stable; use a limited vocabulary.
    if intensity == "quiet":
        if tone == "calming":
            text = "a clean shift, barely a ripple"
        elif tone == "tense":
            text = "quiet with a wary edge"
        else:  # mixed
            text = "a muted day that won’t quite fade"
    elif intensity == "charged":
        if tone == "tense":
            text = "a charge that lingers in muscle memory"
        elif tone == "calming":
            text = "heat remembered as sharpened focus"
        else:
            text = "work under heat that taught vigilance"
    elif intensity == "uneasy":
        # Match example wording
        text = "a low-grade hum of vigilance"
    else:  # oversupervised
        if tone == "calming":
            text = "the kind of quiet that feels watched"
        elif tone == "tense":
            text = "a watched shift that taught caution"
        else:
            text = "a steady gaze that shaped the night"

    return f"Memory Line: {text}."
