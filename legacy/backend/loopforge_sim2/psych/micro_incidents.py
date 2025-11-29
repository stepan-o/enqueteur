from __future__ import annotations

"""
Micro‑Incidents (Sprint N2)

Deterministic, above‑the‑seam generator for tiny per‑day narrative glitches.
Pure function over EpisodeSummary — no mutations, no side effects, no global RNG.

Public API:
- build_micro_incidents(episode: EpisodeSummary) -> list[MicroIncident]

Notes:
- Determinism is achieved by seeding a local RNG per day from (episode_id, day_index)
  using hashlib.sha256. We never touch random.seed() globally.
- Uses existing telemetry only: day tension, per‑agent avg_stress, world pulse hints,
  tension trend, and agent names present that day.
- Generates 0–3 incidents per day.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import hashlib
import random

from loopforge.analytics.reporting import EpisodeSummary, DaySummary, AgentDayStats


# Canonical incident/type enums for this sprint
_INCIDENT_TYPES = ("glitch", "friction", "tension_spike", "weirdness")
_SEVERITY_BANDS = ("low", "medium", "high")


@dataclass(frozen=True)
class MicroIncident:
    day_index: int
    incident_type: str     # "glitch" | "friction" | "tension_spike" | "weirdness"
    severity: str          # "low" | "medium" | "high"
    agents_involved: List[str]
    summary: str


def _clamp01(x: float | int | None) -> float:
    try:
        v = float(0.0 if x is None else x)
    except Exception:
        v = 0.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _severity_from_scalar(s: float) -> str:
    # <0.15 → low; 0.15–0.35 → medium; >0.35 → high
    if s > 0.35:
        return "high"
    if s >= 0.15:
        return "medium"
    return "low"


def _seed_for_day(episode_id: Optional[str], day_index: int) -> int:
    eid = episode_id or "no-ep-id"
    payload = f"{eid}|{int(day_index)}".encode("utf-8")
    h = hashlib.sha256(payload).digest()
    # Use first 8 bytes for a stable 64-bit seed
    return int.from_bytes(h[:8], "big", signed=False)


def _avg_stress(day: DaySummary) -> float:
    vals: List[float] = []
    for s in (day.agent_stats or {}).values():
        try:
            vals.append(float(getattr(s, "avg_stress", 0.0) or 0.0))
        except Exception:
            continue
    return sum(vals) / len(vals) if vals else 0.0


def _pick_agents_for_type(rng: random.Random, day: DaySummary, incident_type: str) -> List[str]:
    names = sorted((day.agent_stats or {}).keys())
    if not names:
        return []
    if incident_type == "friction" and len(names) >= 2:
        i = rng.randrange(len(names))
        # ensure two distinct indices deterministically
        j = (i + 1 + (rng.randrange(len(names) - 1))) % len(names)
        pair = sorted({names[i], names[j]})
        return pair[:2]
    # solo
    idx = rng.randrange(len(names))
    return [names[idx]]


def _templates(incident_type: str, severity: str, agents: List[str]) -> str:
    # Deterministic phrasing based on keys only; no RNG here.
    a1 = agents[0] if agents else "someone"
    a2 = agents[1] if len(agents) > 1 else None
    if incident_type == "glitch":
        if severity == "high":
            return f"Tooling glitch forces {a1} to halt for checks."
        if severity == "medium":
            return f"Noticeable tool glitch near {a1}'s station prompts a pause."
        return f"Minor tool glitch near {a1}'s station."
    if incident_type == "friction":
        if a2:
            if severity == "high":
                return f"{a1} and {a2} lock up over conflicting instructions."
            if severity == "medium":
                return f"{a1} and {a2} hesitate over conflicting instructions."
            return f"{a1} and {a2} briefly talk past each other."
        # Fallback solo phrasing
        return f"{a1} hesitates, unsure which rule to follow."
    if incident_type == "tension_spike":
        if severity == "high":
            return f"A sharp tension spike centers on {a1}."
        if severity == "medium":
            return f"Tension rises around {a1} before settling."
        return f"A brief static around {a1} passes quickly."
    # weirdness
    if severity == "high":
        return f"Ambient weirdness peaks; {a1} double‑checks a baffling anomaly."
    if severity == "medium":
        return f"Sensors jitters make {a1} retrace steps."
    return f"Sensors jitters cause {a1} to double-check a harmless anomaly."


def build_micro_incidents(episode: EpisodeSummary) -> List[MicroIncident]:
    out: List[MicroIncident] = []
    eid = getattr(episode, "episode_id", None)
    for day in episode.days:
        idx = int(getattr(day, "day_index", 0) or 0)
        rng = random.Random(_seed_for_day(eid, idx))
        # Base scalar from normalized avg stress + tension
        s = _avg_stress(day)
        t = _clamp01(getattr(day, "tension_score", 0.0))
        base = _clamp01(0.5 * s + 0.5 * t)
        # Determine how many incidents (0–3) deterministically
        count_cut = [0.80, 0.55, 0.30]  # thresholds for 0/1/2/3
        n = sum(1 for cut in count_cut if base > cut)
        for _ in range(n):
            itype = rng.choice(_INCIDENT_TYPES)
            sev = _severity_from_scalar(base + (rng.random() * 0.1) - 0.05)
            agents = _pick_agents_for_type(rng, day, itype)
            summary = _templates(itype, sev, agents)
            out.append(MicroIncident(day_index=idx, incident_type=itype, severity=sev, agents_involved=agents, summary=summary))
    # Fallback: ensure at least one deterministic, low-severity micro-incident when days exist
    if not out and getattr(episode, "days", None):
        first_day = episode.days[0]
        idx0 = int(getattr(first_day, "day_index", 0) or 0)
        rng0 = random.Random(_seed_for_day(eid, idx0))
        itype = "glitch"
        sev = "low"
        agents = _pick_agents_for_type(rng0, first_day, itype)
        summary = _templates(itype, sev, agents)
        out.append(MicroIncident(day_index=idx0, incident_type=itype, severity=sev, agents_involved=agents, summary=summary))
    return out
