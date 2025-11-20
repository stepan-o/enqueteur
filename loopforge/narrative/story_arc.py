from __future__ import annotations

"""
Deterministic episode-level Story Arc engine (Sprint 8, EA-II)
- Pure, read-only mapping from EpisodeSummary → EpisodeStoryArc
- No randomness, no LLM; lives above the seam
"""
from typing import List, Dict, Optional

from loopforge.schema.types import EpisodeStoryArc
from loopforge.reporting import EpisodeSummary, DaySummary, AgentDayStats


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _mean_stress_for_day(day: DaySummary) -> Optional[float]:
    vals = [float(s.avg_stress or 0.0) for s in (day.agent_stats or {}).values()]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _per_day_stress_means(days: List[DaySummary]) -> List[Optional[float]]:
    return [_mean_stress_for_day(d) for d in days]


def _arc_type_from_stress(days: List[DaySummary]) -> str:
    means = _per_day_stress_means(days)
    if not means or means[0] is None or means[-1] is None:
        return "uncertain"
    start = float(means[0] or 0.0)
    end = float(means[-1] or 0.0)
    delta = end - start
    if delta <= -0.05:
        return "decompression"
    if delta >= 0.05:
        return "escalation"
    # inspect per-day deltas
    deltas: List[float] = []
    prev = None
    for m in means:
        if m is None:
            continue
        if prev is not None:
            deltas.append(m - prev)
        prev = m
    if deltas:
        # sign flips?
        pos = any(x > 0.0 for x in deltas)
        neg = any(x < 0.0 for x in deltas)
        if pos and neg:
            return "back_and_forth"
        # very small changes only
        if all(abs(x) < 0.02 for x in deltas):
            return "flatline"
    return "uncertain"


def _tension_pattern(days: List[DaySummary]) -> str:
    if not days:
        return "unknown"
    tensions = [float(getattr(d, "tension_score", 0.0) or 0.0) for d in days]
    if not tensions:
        return "unknown"
    # steady cooldown: monotonically decreasing by small epsilon
    eps = 1e-6
    non_increasing = all(b <= a + eps for a, b in zip(tensions, tensions[1:]))
    strictly_decreasing_some = any(b < a - 0.01 for a, b in zip(tensions, tensions[1:]))
    if non_increasing and strictly_decreasing_some:
        return "steady_cooldown"
    # spikes: argmax at ends
    max_idx = max(range(len(tensions)), key=lambda i: tensions[i])
    if max_idx == 0:
        return "early_spike"
    if max_idx == len(tensions) - 1:
        return "late_spike"
    return "uneven"


def _supervisor_pattern(days: List[DaySummary]) -> str:
    if not days:
        return "unknown"
    daily_means: List[float] = []
    have_any = False
    for d in days:
        rs_map = getattr(d, "reflection_states", {}) or {}
        if not rs_map:
            daily_means.append(0.0)
            continue
        vals: List[float] = []
        for rs in rs_map.values():
            try:
                vals.append(float(getattr(rs, "supervisor_presence", 0.0) or 0.0))
            except Exception:
                vals.append(0.0)
        if vals:
            have_any = True
            daily_means.append(_mean(vals))
        else:
            daily_means.append(0.0)
    if not have_any:
        return "unknown"
    avg = _mean(daily_means)
    all_low = all(v < 0.2 for v in daily_means)
    if all_low:
        return "hands_off"
    any_high = any(v >= 0.6 for v in daily_means)
    if any_high and avg >= 0.4:
        return "looming"
    if 0.2 <= avg < 0.4:
        return "background"
    # fallback
    return "background" if avg > 0.0 else "unknown"


def _emotional_color(days: List[DaySummary]) -> str:
    if not days:
        return "unknown"
    def _counts_for_day(d: DaySummary) -> Dict[str, int]:
        emo_map = getattr(d, "emotion_states", {}) or {}
        counts = {"calm": 0, "uneasy": 0, "tense": 0, "brittle": 0}
        energies = {"drained": 0, "steady": 0, "wired": 0}
        for es in emo_map.values():
            try:
                m = str(getattr(es, "mood", ""))
                e = str(getattr(es, "energy", ""))
                if m in counts:
                    counts[m] += 1
                if e in energies:
                    energies[e] += 1
            except Exception:
                continue
        counts["_energies_total"] = sum(energies.values())
        counts["_drained"] = energies["drained"]
        counts["_wired"] = energies["wired"]
        return counts
    first = _counts_for_day(days[0]) if days else {}
    last = _counts_for_day(days[-1]) if days else {}
    total_last = max(1, int(last.get("_energies_total", 0)))
    # exhaustion if drained dominates on last day
    if int(last.get("_drained", 0)) >= (total_last // 2 + (total_last % 2)):
        return "exhaustion"
    # wired_to_calm vs calm_to_wired
    if (first.get("tense", 0) + first.get("brittle", 0) + first.get("_wired", 0)) > (first.get("calm", 0)) \
       and (last.get("calm", 0)) >= (last.get("tense", 0) + last.get("brittle", 0)):
        return "wired_to_calm"
    if (first.get("calm", 0)) > (first.get("tense", 0) + first.get("brittle", 0)) and last.get("_wired", 0) > 0:
        return "calm_to_wired"
    # steady calm if calm+steady dominates throughout
    calmish_first = first.get("calm", 0) >= max(1, sum(v for k, v in first.items() if k in {"uneasy","tense","brittle"}))
    calmish_last = last.get("calm", 0) >= max(1, sum(v for k, v in last.items() if k in {"uneasy","tense","brittle"}))
    if calmish_first and calmish_last and last.get("_wired", 0) == 0:
        return "steady_calm"
    # dissonant if moods are roughly balanced across days
    if days:
        swings = False
        for d in (first, last):
            major = max((d.get("calm", 0), d.get("uneasy", 0), d.get("tense", 0), d.get("brittle", 0))) if d else 0
            minor = min((d.get("calm", 0), d.get("uneasy", 0), d.get("tense", 0), d.get("brittle", 0))) if d else 0
            if major - minor <= 1:  # crude balance heuristic
                swings = True
        if swings:
            return "dissonant"
    return "unknown"


def _summary_lines(arc_type: str, tension_pattern: str, supervisor_pattern: str, emotional_color: str,
                   episode: EpisodeSummary) -> List[str]:
    lines: List[str] = []
    # Overall arc line
    if arc_type == "decompression":
        lines.append("The episode opens tight and slowly unwinds.")
    elif arc_type == "escalation":
        lines.append("The episode grows tighter as days progress.")
    elif arc_type == "back_and_forth":
        lines.append("The episode oscillates between pressure and relief.")
    elif arc_type == "flatline":
        lines.append("The episode holds a steady tone with little change.")
    else:
        lines.append("The episode resists a single clear arc.")
    # Tension pattern line
    if tension_pattern == "early_spike":
        lines.append("Tension spikes early before settling.")
    elif tension_pattern == "late_spike":
        lines.append("Tension peaks near the end.")
    elif tension_pattern == "steady_cooldown":
        lines.append("Tension steps down a notch each day.")
    elif tension_pattern == "uneven":
        lines.append("Tension moves unevenly across days.")
    else:
        lines.append("Tension signal is unclear.")
    # Supervisor pattern line
    if supervisor_pattern == "hands_off":
        lines.append("The Supervisor mostly watches from afar.")
    elif supervisor_pattern == "looming":
        lines.append("The Supervisor’s presence feels looming.")
    elif supervisor_pattern == "background":
        lines.append("The Supervisor remains in the background.")
    else:
        lines.append("Supervisor presence is unclear.")
    # Emotional color line
    if emotional_color == "exhaustion":
        lines.append("By the end, most of the floor feels drained rather than panicked.")
    elif emotional_color == "wired_to_calm":
        lines.append("The floor moves from wired energy to calmer footing.")
    elif emotional_color == "calm_to_wired":
        lines.append("Energy ramps up from calm to wired.")
    elif emotional_color == "steady_calm":
        lines.append("Emotional tone stays mostly calm and steady.")
    elif emotional_color == "dissonant":
        lines.append("Emotional signals pull in different directions.")
    else:
        lines.append("Emotional tone is hard to pin down.")
    # Optional numeric facts
    try:
        ts = episode.tension_trend
        if ts:
            lines.append(f"Tension range: {min(ts):.2f} → {max(ts):.2f} (span {max(ts)-min(ts):.2f}).")
    except Exception:
        pass
    return lines[:6]


def derive_episode_story_arc(episode: EpisodeSummary) -> EpisodeStoryArc:
    days = list(episode.days or [])
    arc_type = _arc_type_from_stress(days)
    tension_pat = _tension_pattern(days)
    sup_pat = _supervisor_pattern(days)
    emo_color = _emotional_color(days)
    lines = _summary_lines(arc_type, tension_pat, sup_pat, emo_color, episode)
    return EpisodeStoryArc(
        arc_type=arc_type,
        tension_pattern=tension_pat,
        supervisor_pattern=sup_pat,
        emotional_color=emo_color,
        summary_lines=lines,
    )
