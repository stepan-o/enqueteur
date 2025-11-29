from __future__ import annotations

"""
World Pulse Engine (Sprint A0)

Deterministic, additive, and strictly above the seam.
Generates small environmental disturbances and supervisor mood shifts per day.

Public API:
- compute_world_pulse(day_index: int, *, seed: int | None = None) -> dict

Notes:
- No simulation mechanics or agent behavior are affected.
- This is observational metadata only (for EpisodeSummary and recap views).
- Deterministic: if no seed provided, derive local seed as
    seed = (day_index * 7919) % 65536
- Uses Python's random.Random(seed) for stable pseudo-random choices.
"""

from typing import Dict, Any, Optional
import random

ENVIRONMENTAL_ANOMALIES = [
    "heat_spike",
    "vibration_drift",
    "red_haze",
    "air_thickening",
    "silence_drop",
]

SYSTEM_FAILURES = [
    "none",
    "minor",
    "moderate",
]

MICRO_INCIDENTS = [
    "spark_pop",
    "jammed_gear",
    "off_calibration",
    "none",
]

SUPERVISOR_TONES = [
    "supportive",
    "neutral",
    "tense",
    "authoritarian",
]


def compute_world_pulse(day_index: int, *, seed: Optional[int] = None) -> Dict[str, Any]:
    """Compute a deterministic world pulse dictionary for the given day.

    Required keys and constraints:
      - "environmental_anomaly": one of ENVIRONMENTAL_ANOMALIES
      - "system_failure": one of SYSTEM_FAILURES
      - "micro_incident": one of MICRO_INCIDENTS
      - "supervisor_tone": one of SUPERVISOR_TONES
      - "ambient_tension_delta": small float in [-0.05, +0.05]
      - "motive_pressure": small float in [0.0, 1.0]

    Determinism:
      - If seed is provided, output is stable given the seed.
      - Otherwise seed = (day_index * 7919) % 65536
    """
    local_seed = seed if seed is not None else (int(day_index) * 7919) % 65536
    rng = random.Random(local_seed)

    environmental_anomaly = rng.choice(ENVIRONMENTAL_ANOMALIES)
    system_failure = rng.choice(SYSTEM_FAILURES)
    micro_incident = rng.choice(MICRO_INCIDENTS)
    supervisor_tone = rng.choice(SUPERVISOR_TONES)

    # Small float between -0.05 and +0.05 (inclusive bounds tolerated)
    ambient_tension_delta = rng.uniform(-0.05, 0.05)

    # Motive pressure as a day-level scalar in [0.0, 1.0]
    motive_pressure = rng.random()

    return {
        "environmental_anomaly": environmental_anomaly,
        "system_failure": system_failure,
        "micro_incident": micro_incident,
        "supervisor_tone": supervisor_tone,
        "ambient_tension_delta": float(ambient_tension_delta),
        "motive_pressure": float(motive_pressure),
    }
