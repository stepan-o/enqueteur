from __future__ import annotations

"""
Episode-level Psychology Board renderer.

- Pure, deterministic helpers that live above the seam.
- No randomness, no side effects.
- Builds a compact table for the whole episode using DaySummary fields:
  - agent_stats.avg_stress -> stress band (low|mid|high)
  - belief_attributions[agent].cause -> R/S/U/F letter
  - emotion_states[agent].mood -> ?, ., ✓, ! bucket
"""
from typing import List, Dict, Set

from loopforge.reporting import EpisodeSummary, DaySummary

# Reuse the exact Sprint 1 thresholds by importing the daily log helper
try:
    from .daily_logs import _stress_band as _daily_stress_band  # type: ignore
except Exception:  # pragma: no cover - defensive fallback
    def _daily_stress_band(x: float) -> str:  # type: ignore
        if x > 0.3:
            return "high"
        if x >= 0.08:
            return "mid"
        return "low"


def stress_band(value: float) -> str:
    """Map stress value to band using the same thresholds as Daily Logs.
    low < 0.08, mid 0.08–0.30, high > 0.30
    """
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return _daily_stress_band(v)


def attr_cause_to_letter(cause: str | None) -> str:
    """Map attribution cause keyword to one-letter code.
    random->R, system->S, supervisor->U, self->F; unknown -> '-'
    """
    m = {
        "random": "R",
        "system": "S",
        "supervisor": "U",
        "self": "F",
    }
    try:
        key = str(cause) if isinstance(cause, str) else None
    except Exception:
        key = None
    return m.get(key or "", "-")


def mood_to_bucket(mood: str | None) -> str:
    """Map EA-1 mood to glyph bucket.
    calm->✓, uneasy->?, tense/brittle->!, unknown/other->.
    """
    try:
        m = str(mood) if isinstance(mood, str) else None
    except Exception:
        m = None
    if m == "calm":
        return "✓"
    if m == "uneasy":
        return "?"
    if m in {"tense", "brittle"}:
        return "!"
    return "."


def _all_agent_names(days: List[DaySummary]) -> List[str]:
    seen: Set[str] = set()
    for d in days:
        try:
            for name in d.agent_stats.keys():
                seen.add(name)
        except Exception:
            continue
    return sorted(seen)


def cell_code(day: DaySummary, agent_name: str) -> str:
    """Return "<stress>/<attrLetter>/<moodGlyph>" for a given agent/day.
    Fail-soft defaults ensure determinism when data is missing.
    """
    # Stress
    try:
        stats = day.agent_stats.get(agent_name)
        s_val = float(getattr(stats, "avg_stress", 0.0) or 0.0) if stats is not None else None
    except Exception:
        stats = None
        s_val = None
    s_band = stress_band(0.0 if s_val is None else s_val)

    # Attribution letter
    try:
        attr_map = getattr(day, "belief_attributions", {}) or {}
        attr = attr_map.get(agent_name)
        cause = getattr(attr, "cause", None) if attr is not None else None
    except Exception:
        cause = None
    a_letter = attr_cause_to_letter(cause)

    # Mood bucket
    try:
        emo_map = getattr(day, "emotion_states", {}) or {}
        emo = emo_map.get(agent_name)
        mood = getattr(emo, "mood", None) if emo is not None else None
    except Exception:
        mood = None
    m_bucket = mood_to_bucket(mood)

    return f"{s_band}/{a_letter}/{m_bucket}"


def build_psych_board(episode: EpisodeSummary) -> List[str]:
    """Build the Psychology Board as a list of printable lines.
    Layout:
      PSYCHOLOGY BOARD
      =================
      Days:   0      1      2
      -------------------------------------
      <Agent>  <cell0>  <cell1>  <cell2>
    """
    days: List[DaySummary] = list(getattr(episode, "days", []) or [])
    day_count = len(days)

    # Header
    lines: List[str] = []
    lines.append("PSYCHOLOGY BOARD")
    lines.append("================")
    # Days header line
    day_labels = " ".join(str(i) for i in range(day_count))
    # Add extra spacing to align roughly with columns; exact spacing not strict
    lines.append(f"Days:   {day_labels if day_labels else ''}")
    lines.append("-" * 37)

    # Rows per agent (sorted)
    names = _all_agent_names(days)
    for name in names:
        cells: List[str] = []
        for idx in range(day_count):
            d = days[idx]
            cells.append(cell_code(d, name))
        # Join cells with two spaces for readability
        row = f"{name.ljust(8)}  " + "  ".join(cells)
        lines.append(row)

    return lines
