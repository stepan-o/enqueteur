from __future__ import annotations
"""
Arc Cohesion helpers (pure, deterministic, above the seam).

Sprint 4 goal: Provide a one-line, deterministic verdict describing how well the
episode STORY ARC aligns with aggregate agent reflections (approximated by
final per-agent stress levels).

No randomness, no side effects. Read-only over EpisodeSummary.
"""
from typing import Optional, List

from .reporting import EpisodeSummary
from .types import EpisodeStoryArc


def _majority_label(labels: List[str]) -> str:
    counts = {}
    for l in labels:
        if not l:
            continue
        counts[l] = counts.get(l, 0) + 1
    if not counts:
        return "mixed"
    return max(counts, key=counts.get)


def compute_reflection_tone(episode: EpisodeSummary) -> str:
    """Derive a coarse reflection tone from per-agent final stress.

    Rules (deterministic):
    - For each agent in episode.agents, take stress_end (float in [0,1]).
      * stress_end < 0.10  -> label "calming"
      * stress_end > 0.30  -> label "tense"
      * otherwise          -> label "neutral"
    - Unique majority vote over labels: if a single label dominates and is
      "calming" or "tense", return it; ties or neutral dominance -> "mixed".
    - If there are no agents or stress_end is missing everywhere -> "mixed".
    """
    try:
        agents = getattr(episode, "agents", {}) or {}
    except Exception:
        agents = {}
    counts = {"calming": 0, "tense": 0, "neutral": 0}
    for a in agents.values():
        try:
            end = getattr(a, "stress_end", None)
            if end is None:
                continue
            v = float(end)
        except Exception:
            continue
        if v < 0.10:
            counts["calming"] += 1
        elif v > 0.30:
            counts["tense"] += 1
        else:
            counts["neutral"] += 1
    total = sum(counts.values())
    if total == 0:
        return "mixed"
    top = max(counts.values())
    winners = [k for k, c in counts.items() if c == top]
    if len(winners) != 1:
        return "mixed"
    winner = winners[0]
    return winner if winner in {"calming", "tense"} else "mixed"


def compute_arc_cohesion(story_arc_type: str, reflection_tone: str) -> str:
    """Map (story arc, reflection tone) to a deterministic verdict.

    The story arc types in EpisodeStoryArc are mapped to the table from the sprint:
    - "decompression" ~= "unwinding"
    - "escalation"    ~= "building tension"
    - others           -> treated as "other/mixed"

    Deterministic rule table:
    story_arc          reflection tone    result
    unwinding          calming            cohesive episode arc
    unwinding          tense              fragmented arc
    building tension   calming            mild mismatch
    building tension   tense              cohesive episode arc
    anything else      mixed              mild mismatch
    catch-all          any                mild mismatch
    """
    # Normalize arc bucket
    arc_bucket = "other"
    s = (story_arc_type or "").strip().lower()
    if s == "decompression":
        arc_bucket = "unwinding"
    elif s == "escalation":
        arc_bucket = "building tension"
    # Normalize tone
    tone = (reflection_tone or "mixed").strip().lower()

    if arc_bucket == "unwinding":
        if tone == "calming":
            return "cohesive episode arc"
        if tone == "tense":
            return "fragmented arc"
        return "mild mismatch"
    if arc_bucket == "building tension":
        if tone == "tense":
            return "cohesive episode arc"
        if tone == "calming":
            return "mild mismatch"
        return "mild mismatch"
    # anything else
    if tone == "mixed":
        return "mild mismatch"
    # catch-all
    return "mild mismatch"


def build_arc_cohesion_line(episode_summary: EpisodeSummary, story_arc: Optional[EpisodeStoryArc]) -> str:
    """Return a single deterministic sentence describing arc cohesion.

    Example outputs:
    - "Arc Cohesion: cohesive episode arc (story arc vs reflections aligned)."
    - "Arc Cohesion: fragmented arc (story arc and reflections disagree)."
    - "Arc Cohesion: mild mismatch (weak alignment)."
    """
    tone = compute_reflection_tone(episode_summary)
    try:
        arc_type = getattr(story_arc, "arc_type", "uncertain") if story_arc is not None else "uncertain"
    except Exception:
        arc_type = "uncertain"
    verdict = compute_arc_cohesion(arc_type, tone)
    # Choose a short parenthetical to keep deterministic phrasing
    if verdict == "cohesive episode arc":
        suffix = "(story arc vs reflections aligned)."
    elif verdict == "fragmented arc":
        suffix = "(story arc and reflections disagree)."
    else:
        suffix = "(weak alignment)."
    return f"Arc Cohesion: {verdict} {suffix}"