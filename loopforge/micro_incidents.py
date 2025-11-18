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

from .reporting import EpisodeSummary, DaySummary, AgentDayStats


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


def _decide_incident_types(
    rng: random.Random,
    day: DaySummary,
    episode: EpisodeSummary,
    severity: str,
) -> List[str]:
    # Bias by tension and world pulse
    types: List[str] = []

    tension = _clamp01(getattr(day, "tension_score", 0.0))
    # Rising overall if last > first by small epsilon
    trend_rising = False
    try:
        tt = list(getattr(episode, "tension_trend", []) or [])
        trend_rising = bool(tt and (float(tt[-1]) - float(tt[0]) > 0.05))
    except Exception:
        trend_rising = False

    # World pulse hints
    wph = getattr(episode, "world_pulse_history", None)
    pulse = None
    if isinstance(wph, list) and 0 <= day.day_index < len(wph):
        try:
            pulse = wph[day.day_index]
        except Exception:
            pulse = None
    anomaly = None
    micro_hint = None
    if isinstance(pulse, dict):
        anomaly = pulse.get("environmental_anomaly")
        micro_hint = pulse.get("micro_incident")

    # Decide a base count (0..3) with gentle bias by severity
    # high -> 2, medium ->1, low -> 0 or 1
    if severity == "high":
        base_count = 2
    elif severity == "medium":
        base_count = 1
    else:
        base_count = 1 if tension > 0.10 else 0

    # Allow RNG to sometimes add one more within cap 3 (deterministic under seed)
    if base_count < 3 and rng.random() < 0.25:
        base_count += 1
    base_count = max(0, min(3, base_count))

    # Build candidate pool with biases
    for _ in range(base_count):
        choice_pool: List[str] = ["glitch"]
        if tension > 0.35 or trend_rising:
            choice_pool.extend(["tension_spike", "friction"])  # add pressure types
        if isinstance(anomaly, str) and anomaly in {"vibration_drift", "air_thickening", "red_haze", "heat_spike"}:
            choice_pool.append("weirdness")
        if isinstance(micro_hint, str) and micro_hint != "none":
            # If world pulse suggested something, lean toward a non-glitch
            choice_pool.append("weirdness")
        # Deterministic pick
        itype = choice_pool[rng.randrange(len(choice_pool))]
        types.append(itype)

    return types


def build_micro_incidents(episode: "EpisodeSummary") -> List[MicroIncident]:
    """Derive per‑day micro‑incidents from EpisodeSummary telemetry.

    Pure and deterministic:
    - Does not mutate `episode`.
    - Uses only a local Random seeded from (episode_id, day_index).
    - Returns up to 3 incidents per day.
    """
    out: List[MicroIncident] = []
    days: List[DaySummary] = list(getattr(episode, "days", []) or [])
    eid: Optional[str] = getattr(episode, "episode_id", None)

    for day in days:
        seed = _seed_for_day(eid, int(getattr(day, "day_index", 0) or 0))
        rng = random.Random(seed)

        # Signals
        day_tension = _clamp01(getattr(day, "tension_score", 0.0))
        avg_st = _avg_stress(day)
        scalar = _clamp01(0.5 * day_tension + 0.5 * avg_st)
        severity = _severity_from_scalar(scalar)

        # Decide types and agents
        types = _decide_incident_types(rng, day, episode, severity)
        for it in types:
            agents = _pick_agents_for_type(rng, day, it)
            summary = _templates(it, severity, agents)
            out.append(
                MicroIncident(
                    day_index=int(getattr(day, "day_index", 0) or 0),
                    incident_type=it,
                    severity=severity,
                    agents_involved=list(agents),
                    summary=summary,
                )
            )

    # Deterministic order across days/types/agents
    out.sort(key=lambda mi: (mi.day_index, mi.incident_type, tuple(mi.agents_involved)))
    return out
