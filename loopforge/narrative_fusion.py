from __future__ import annotations

"""
Narrative Fusion (Sprint N1)

Deterministic, additive, above-the-seam synthesis of a per-day "Day Narrative
Kernel" that fuses existing telemetry signals into a compact, machine-readable
structure plus a single human-readable synthesis line.

This module does not modify simulation mechanics or logging. It only reads
DaySummary objects and derives a kernel for narrative layers to consume.

Public API:
- build_day_narrative_kernel(day_summary: DaySummary) -> DayNarrativeKernel

Notes:
- All computations are deterministic and template-based.
- Missing inputs must never crash the builder; we default to zeros and
  conservative labels.
- Constants at the top control weighting and thresholds so future tuning
  remains explicit and testable.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .reporting import DaySummary, AgentDayStats

# ---------------------- Tunable constants (deterministic) ---------------------

# Supervisor tone mapping thresholds based on normalized supervisor_activity
SUP_TONE_THRESHOLDS = {
    "supportive": 0.20,  # <= 0.20
    "neutral": 0.40,     # <= 0.40
    "concerned": 0.70,   # <= 0.70
    # >0.70 => "critical"
}

# Fragility thresholds
STRESS_HIGH = 0.60
GUARDRAIL_RIGID = 0.75
CONTEXT_LOW_AVOID = 0.25
MEMORY_DRIFT_CONFUSED = 0.60

# Global pressure weights — keep explicit for future tuning
W_TENSION = 0.45
W_DISTORTIONS = 0.20
W_SUPERVISOR = 0.20
W_FRAGILITY = 0.15

# Pressure banding for synthesis text
PRESSURE_HIGH = 0.66
PRESSURE_MID = 0.33


@dataclass
class DayNarrativeKernel:
    day_index: int
    global_pressure: float
    supervisor_tone: str
    dominant_fragility: str
    distortion_vector: Dict[str, float]
    memory_drift_vector: Dict[str, float]
    stress_trend: str
    synthesis_line: str


# ----------------------------- helpers ---------------------------------------

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


def _map_supervisor_tone(supervisor_activity: float) -> str:
    a = _clamp01(supervisor_activity)
    if a <= SUP_TONE_THRESHOLDS["supportive"]:
        return "supportive"
    if a <= SUP_TONE_THRESHOLDS["neutral"]:
        return "neutral"
    if a <= SUP_TONE_THRESHOLDS["concerned"]:
        return "concerned"
    return "critical"


def _guardrail_ratio(stats: AgentDayStats) -> float:
    g = float(getattr(stats, "guardrail_count", 0) or 0)
    c = float(getattr(stats, "context_count", 0) or 0)
    total = g + c
    return 1.0 if total <= 0.0 else g / total


def _context_ratio(stats: AgentDayStats) -> float:
    g = float(getattr(stats, "guardrail_count", 0) or 0)
    c = float(getattr(stats, "context_count", 0) or 0)
    total = g + c
    return 0.0 if total <= 0.0 else c / total


def _derive_memory_drift_signals(day: DaySummary) -> Dict[str, float]:
    """Aggregate coarse memory drift signals from reflection/emotion states when present.

    The keys here are scaffolding for future richer signals. Today we probe for
    common attribute names on per-agent states and average them to a day-level
    vector. Missing signals produce zeros.
    """
    # Candidate keys we expose in the vector
    keys = ("coherence_drop", "recall_mismatch", "memory_drift")
    accum = {k: 0.0 for k in keys}
    count = {k: 0 for k in keys}

    def _extract(v: object, attr: str) -> Optional[float]:
        try:
            val = getattr(v, attr, None)
            if val is None and isinstance(v, dict):
                val = v.get(attr)
            if val is None and attr == "memory_drift":
                # fallbacks seen in other modules
                for alt in ("drift", "instability", "coherence_inverse"):
                    altv = getattr(v, alt, None) if not isinstance(v, dict) else v.get(alt)
                    if altv is not None:
                        val = altv
                        break
            if val is None:
                return None
            f = float(val)
            return _clamp01(f)
        except Exception:
            return None

    # Probe reflection_states then emotion_states
    for container in (getattr(day, "reflection_states", {}) or {}, getattr(day, "emotion_states", {}) or {}):
        if not isinstance(container, dict):
            continue
        for _name, state in container.items():
            for k in keys:
                v = _extract(state, k)
                if v is None:
                    continue
                accum[k] += v
                count[k] += 1

    # Average
    out = {}
    for k in keys:
        if count[k] > 0:
            out[k] = _clamp01(accum[k] / max(1, count[k]))
        else:
            out[k] = 0.0
    return out


def _derive_distortion_vector(day: DaySummary) -> Dict[str, float]:
    """Build belief distortion vector.

    We expose three canonical keys. If indicators are unavailable, we return zeros.
    If available in day.beliefs or day.belief_attributions, map them into [0,1].
    """
    out = {"catastrophizing": 0.0, "confirmation_bias": 0.0, "self_blame": 0.0}

    # Attempt to infer from belief_attributions severity if available
    try:
        attrs = getattr(day, "belief_attributions", {}) or {}
        for _name, obj in attrs.items():
            # Heuristics: look for numeric attributes likely to correlate
            for key, candidates in (
                ("self_blame", ("self_blame", "self_blame_score")),
                ("confirmation_bias", ("confirmation_bias", "confirmation")),
                ("catastrophizing", ("catastrophizing", "alarmism")),
            ):
                for cand in candidates:
                    v = getattr(obj, cand, None)
                    if v is None and isinstance(obj, dict):
                        v = obj.get(cand)
                    if v is not None:
                        try:
                            out[key] = max(out[key], _clamp01(float(v)))
                        except Exception:
                            pass
    except Exception:
        pass

    return out


def _classify_fragility(stats: AgentDayStats, mem_drift_score: float) -> Tuple[str, float]:
    """Return (label, severity) for an agent.

    Severity is a 0..1 scalar used to pick a dominant fragility across agents.
    Deterministic priority via severity then tie-breaker by label order.
    """
    stress = _clamp01(getattr(stats, "avg_stress", 0.0))
    g_ratio = _clamp01(_guardrail_ratio(stats))
    c_ratio = _clamp01(_context_ratio(stats))
    drift = _clamp01(mem_drift_score)

    # Evaluate categories; assign severity as the key signal driving it
    if stress >= STRESS_HIGH:
        return "stressed", stress
    if drift >= MEMORY_DRIFT_CONFUSED:
        return "confused", drift
    if g_ratio >= GUARDRAIL_RIGID:
        return "rigid", g_ratio
    if c_ratio <= CONTEXT_LOW_AVOID and stress <= 0.40:
        sev = max(1.0 - c_ratio, 0.0)
        return "avoidant", _clamp01(sev)
    return "balanced", 0.25  # low severity baseline


def _dominant_fragility(day: DaySummary, mem_vec: Dict[str, float]) -> str:
    best_label = "balanced"
    best_sev = -1.0
    # Precompute a per-agent drift proxy (use max of vector as drift score)
    drift_score = max(mem_vec.values()) if mem_vec else 0.0
    for name in sorted((day.agent_stats or {}).keys()):  # deterministic iteration
        stats = day.agent_stats[name]
        label, sev = _classify_fragility(stats, drift_score)
        if sev > best_sev or (sev == best_sev and label < best_label):
            best_sev = sev
            best_label = label
    return best_label


def _stress_trend(day: DaySummary) -> str:
    """Best-effort stress trend for the day: rising/falling/flat.

    With a single DaySummary we cannot compare across days reliably; when no
    explicit delta is found, we return "flat".
    """
    # Try to infer from emotion_states average delta fields if present
    try:
        es = getattr(day, "emotion_states", {}) or {}
        deltas = []
        for _name, st in es.items():
            for cand in ("stress_delta", "delta_stress", "stress_slope"):
                v = getattr(st, cand, None)
                if v is None and isinstance(st, dict):
                    v = st.get(cand)
                if v is not None:
                    deltas.append(float(v))
                    break
        if deltas:
            avg = sum(deltas) / len(deltas)
            if avg > 1e-6:
                return "rising"
            if avg < -1e-6:
                return "falling"
            return "flat"
    except Exception:
        pass
    # Fallback: flat
    return "flat"


def _fragility_severity_scalar(label: str) -> float:
    return {
        "stressed": 1.0,
        "confused": 0.8,
        "rigid": 0.6,
        "avoidant": 0.4,
        "balanced": 0.2,
    }.get(label, 0.2)


def _supervisor_scalar(tone: str) -> float:
    return {
        "supportive": 0.1,
        "neutral": 0.3,
        "concerned": 0.6,
        "critical": 1.0,
    }.get(tone, 0.3)


def _compute_global_pressure(tension: float, distortions: Dict[str, float], tone: str, fragility: str) -> float:
    t = _clamp01(tension)
    d_sum = sum(_clamp01(v) for v in (distortions or {}).values())
    d_norm = _clamp01(d_sum / max(1, len(distortions) or 1))
    s_sup = _supervisor_scalar(tone)
    s_frag = _fragility_severity_scalar(fragility)
    score = (W_TENSION * t) + (W_DISTORTIONS * d_norm) + (W_SUPERVISOR * s_sup) + (W_FRAGILITY * s_frag)
    return _clamp01(score)


def _build_synthesis_line(pressure: float, tone: str, fragility: str) -> str:
    # Lead with pressure state
    if pressure >= PRESSURE_HIGH:
        p_txt = "Pressure is high"
    elif pressure >= PRESSURE_MID:
        p_txt = "Pressure is building"
    else:
        p_txt = "Pressure is low"

    # Tone phrase
    tone_map = {
        "supportive": "Supervisor tone is supportive",
        "neutral": "Supervisor tone stays neutral",
        "concerned": "Supervisor tone turned concerned",
        "critical": "Supervisor tone turned critical",
    }
    tone_txt = tone_map.get(tone, "Supervisor tone stays neutral")

    # Fragility phrase
    if fragility in ("stressed", "rigid", "confused", "avoidant"):
        frag_txt = f"dominant fragility: {fragility}"
    else:
        frag_txt = "team remains balanced"

    return f"{p_txt}; {tone_txt}; {frag_txt}."


# --------------------------- public API --------------------------------------

def build_day_narrative_kernel(day_summary: DaySummary) -> DayNarrativeKernel:
    """Fuse DaySummary signals into a DayNarrativeKernel.

    - Extracts normalized numeric signals
    - Classifies agent fragilities deterministically
    - Builds belief distortion and memory drift vectors (zeros if absent)
    - Computes a global pressure scalar in [0,1]
    - Produces a single-line human summary with pressure/tone/fragility
    """
    d = day_summary
    day_index = int(getattr(d, "day_index", 0) or 0)

    tension = _clamp01(getattr(d, "tension_score", 0.0))
    sup_activity = _clamp01(getattr(d, "supervisor_activity", 0.0))
    tone = _map_supervisor_tone(sup_activity)

    mem_vec = _derive_memory_drift_signals(d)
    dist_vec = _derive_distortion_vector(d)

    dom_frag = _dominant_fragility(d, mem_vec)

    pressure = _compute_global_pressure(tension, dist_vec, tone, dom_frag)

    trend = _stress_trend(d)

    synthesis = _build_synthesis_line(pressure, tone, dom_frag)

    return DayNarrativeKernel(
        day_index=day_index,
        global_pressure=pressure,
        supervisor_tone=tone,
        dominant_fragility=dom_frag,
        distortion_vector=dist_vec,
        memory_drift_vector=mem_vec,
        stress_trend=trend,
        synthesis_line=synthesis,
    )
