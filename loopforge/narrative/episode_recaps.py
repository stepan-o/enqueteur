from __future__ import annotations

"""
Pure, deterministic episode recap builder over telemetry summaries.

Constraints:
- Read-only over EpisodeSummary/DaySummary and character metadata.
- No simulation/logging/reflection changes.
- Deterministic, template-based strings; no randomness.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Mapping, Any

from loopforge.analytics.reporting import EpisodeSummary, DaySummary, AgentEpisodeStats


@dataclass
class EpisodeRecap:
    intro: str
    per_agent_blurbs: Dict[str, str]
    closing: str
    # Sprint 8: Optional story arc lines to render as a block in recap output
    story_arc_lines: List[str] | None = None
    # Sprint A0: Optional world pulse lines block (deterministic)
    world_pulse_lines: List[str] | None = None
    # Sprint N2: Optional micro-incidents lines block (deterministic)
    micro_incident_lines: List[str] | None = None
    # Sprint 12: Optional Arc Cohesion one-liner (deterministic)
    arc_cohesion: str | None = None
    # Sprint 13: Optional Memory Line one-liner (deterministic)
    memory_line: str | None = None
    # Sprint 10: Optional memory drift lines block
    memory_lines: List[str] | None = None
    # Sprint A1: Optional attribution/distortion lines block
    distortion_lines: List[str] | None = None
    # Sprint 11: Optional pressure notes lines block (additive, deterministic)
    pressure_lines: List[str] | None = None


# ----------------------------- Helpers ---------------------------------

def _tension_overall_trend(tensions: List[float], eps: float = 0.05) -> str:
    """Classify overall trend using first vs last value with epsilon threshold.
    Returns one of: "rising", "falling", "flat".
    """
    if not tensions:
        return "flat"
    start, end = tensions[0], tensions[-1]
    delta = float(end) - float(start)
    if delta > eps:
        return "rising"
    if delta < -eps:
        return "falling"
    return "flat"


def _stress_band(x: Optional[float]) -> str:
    """Stress bands for episode recap text.
    Note: tests expect 0.10 to be treated as "low" here (slightly looser than
    the day-narrative bands). We intentionally use a <=0.10 cutoff locally to
    keep recap phrasing aligned with episode-level expectations without
    affecting other modules.
    """
    v = 0.0 if x is None else float(x)
    if v > 0.3:
        return "high"
    if v > 0.10:
        return "mid"
    return "low"


def _stress_arc_phrase(start: Optional[float], end: Optional[float], eps: float = 1e-6) -> Tuple[str, str, str]:
    """Return (start_band, end_band, arc_keyword) with exact keywords required by brief.
    arc_keyword in {"tightened over the episode", "gradually unwound", "held steady"}
    """
    sb = _stress_band(start)
    eb = _stress_band(end)
    s = 0.0 if start is None else float(start)
    e = 0.0 if end is None else float(end)
    if e - s > eps:
        arc = "tightened over the episode"
    elif e - s < -eps:
        arc = "gradually unwound"
    else:
        arc = "held steady"
    return sb, eb, arc


def _guardrail_phrase(total_guardrail: int, total_context: int) -> Optional[str]:
    total = int(total_guardrail) + int(total_context)
    if total > 0 and int(total_guardrail) == total:
        # Exact template per brief
        return "stayed strictly within guardrails"
    return None


def _role_flavor(name: str, role: str, characters: Mapping[str, Mapping[str, Any]] | None) -> Optional[str]:
    if not characters:
        return None
    spec = characters.get(name)
    if not isinstance(spec, Mapping):
        # Try matching by role if name not present (optional, fail-soft)
        return None
    # Prefer vibe, then tagline, else None
    vibe = spec.get("vibe")
    if isinstance(vibe, str) and vibe:
        return vibe
    tag = spec.get("tagline")
    if isinstance(tag, str) and tag:
        return tag
    return None


# ----------------------------- Public API ---------------------------------

def build_episode_recap(
    episode_summary: EpisodeSummary,
    day_summaries: List[DaySummary],
    characters: Dict[str, Mapping[str, Any]]
) -> EpisodeRecap:
    """Build an EpisodeRecap from telemetry summaries and character metadata.

    Templates per spec:
    - Tension intro: exact three strings (rising/falling/flat).
    - Agent arc keywords: exact (tightened over the episode / gradually unwound / held steady).
    - Guardrail behavior: if guardrail == total_steps → "stayed strictly within guardrails".
    - Closing tone based on final tension (high/medium/low).
    """
    # Intro from overall tension trend
    trend = _tension_overall_trend(list(episode_summary.tension_trend))
    if trend == "rising":
        intro = "The episode runs hot; tension climbs from start to finish."
    elif trend == "falling":
        intro = "The episode eases off; the early edge softens over time."
    else:
        intro = "The episode holds steady with no major shifts in tension."

    # Per-agent blurbs in deterministic order (alphabetical by name)
    per_agent: Dict[str, str] = {}
    for name in sorted(episode_summary.agents.keys()):
        a: AgentEpisodeStats = episode_summary.agents[name]
        sb, eb, arc_kw = _stress_arc_phrase(a.stress_start, a.stress_end)
        guardrail_note = _guardrail_phrase(a.guardrail_total, a.context_total)
        flavor = _role_flavor(name, a.role, characters)

        # Compose 1–2 sentences deterministically
        # Sentence 1: stress arc + bands
        first = (
            f"{name} ({a.role}) moved from {sb} stress to {eb} and {arc_kw}."
        )
        # Sentence 2: optional guardrail-only + soft flavor
        second_parts: List[str] = []
        if guardrail_note:
            second_parts.append(guardrail_note)
        if flavor:
            second_parts.append(flavor)
        second = None
        if second_parts:
            # Join with "; " for compactness, end with period.
            second = "; ".join(second_parts) + "."

        # Optional sentence 3: Belief drift (supervisor_trust start → end)
        belief_line = None
        try:
            if day_summaries:
                first_day = day_summaries[0]
                last_day = day_summaries[-1]
                b0 = (getattr(first_day, "beliefs", {}) or {}).get(name)
                b1 = (getattr(last_day, "beliefs", {}) or {}).get(name)
                if b0 is not None and b1 is not None:
                    belief_line = f"Belief drift: supervisor trust {round(float(b0.supervisor_trust), 2)} → {round(float(b1.supervisor_trust), 2)}."
        except Exception:
            belief_line = None

        # Optional sentence 4: Attribution arc (first and last day causes)
        attr_line = None
        try:
            if day_summaries:
                a0 = getattr(day_summaries[0], "belief_attributions", {}) or {}
                a1 = getattr(day_summaries[-1], "belief_attributions", {}) or {}
                c0 = getattr(a0.get(name), "cause", None) if a0 else None
                c1 = getattr(a1.get(name), "cause", None) if a1 else None
                if isinstance(c0, str) and c0 and isinstance(c1, str) and c1:
                    attr_line = f"Attribution pattern: mostly {c0} → {c1}."
        except Exception:
            attr_line = None

        pieces = [first]
        if second:
            pieces.append(second)
        if belief_line:
            pieces.append(belief_line)
        if attr_line:
            pieces.append(attr_line)
        per_agent[name] = " ".join(pieces)

    # Closing based on final tension
    final_tension = episode_summary.tension_trend[-1] if episode_summary.tension_trend else 0.0
    if final_tension > 0.6:
        closing = "The shift closes under a lingering edge."
    elif final_tension >= 0.3:
        closing = "The shift ends balanced and steady."
    else:
        closing = "The shift winds down quietly, nothing pressing."

    # Sprint 8: Optional story arc block from EpisodeSummary.story_arc
    story_arc_lines: List[str] | None = None
    try:
        arc = getattr(episode_summary, "story_arc", None)
        if arc is not None and getattr(arc, "summary_lines", None):
            story_arc_lines = list(getattr(arc, "summary_lines"))
    except Exception:
        story_arc_lines = None

    # Sprint A0: Optional WORLD PULSE lines from EpisodeSummary.world_pulse_history
    world_pulse_lines: List[str] | None = None
    try:
        wph = getattr(episode_summary, "world_pulse_history", None)
        if isinstance(wph, list) and wph:
            lines: List[str] = []
            for idx, pulse in enumerate(wph):
                try:
                    tone = pulse.get("supervisor_tone", "neutral")
                    anomaly = pulse.get("environmental_anomaly", "silence_drop")
                    sysfail = pulse.get("system_failure", "none")
                    micro = pulse.get("micro_incident", "none")
                    lines.append(f"Day {idx}: {tone}, {anomaly}, {sysfail}, {micro}")
                except Exception:
                    continue
            if lines:
                world_pulse_lines = lines
    except Exception:
        world_pulse_lines = None

    # Sprint N2: Optional MICRO-INCIDENTS lines derived from episode telemetry
    micro_incident_lines: List[str] | None = None
    try:
        from loopforge.micro_incidents import build_micro_incidents
        incidents = build_micro_incidents(episode_summary)
        if incidents:
            # Deterministic string rendering
            lines: List[str] = []
            for mi in incidents:
                agents_txt = ", ".join(mi.agents_involved) if mi.agents_involved else ""
                # Preserve short summary in the line, prefix with day
                sev = f" ({mi.severity})" if mi.severity else ""
                if agents_txt and agents_txt not in mi.summary:
                    line = f"Day {mi.day_index} — {mi.summary}"
                else:
                    line = f"Day {mi.day_index} — {mi.summary}"
                # Append severity tag for quick scanning
                line = f"{line} {sev}".rstrip()
                lines.append(line)
            # Sort lines by (day_index, then stable string)
            lines.sort()
            micro_incident_lines = lines
    except Exception:
        micro_incident_lines = None

    # Sprint 10: Optional memory drift block from EpisodeSummary.long_memory
    memory_lines: List[str] | None = None
    try:
        lm = getattr(episode_summary, "long_memory", None)
        if isinstance(lm, dict) and lm:
            lines: List[str] = []
            # Deterministic order: alphabetical by agent name, max 4 lines
            for name in sorted(lm.keys()):
                try:
                    mem = lm[name]
                    agency = float(getattr(mem, "agency", 0.5) or 0.5)
                    stability = float(getattr(mem, "stability", 0.5) or 0.5)
                    trust_sup = float(getattr(mem, "trust_supervisor", 0.5) or 0.5)
                    self_tr = float(getattr(mem, "self_trust", 0.5) or 0.5)
                    reactivity = float(getattr(mem, "reactivity", 0.5) or 0.5)
                    line = None
                    if agency > 0.6 and stability > 0.5:
                        line = f"{name}: growing more sure-footed with each shift."
                    elif trust_sup < 0.4 and self_tr < 0.4:
                        line = f"{name}: trust in both self and Supervisor is eroding."
                    elif stability < 0.4 and reactivity > 0.6:
                        line = f"{name}: simmering, more reactive and less stable over time."
                    if line:
                        lines.append(line)
                except Exception:
                    continue
                if len(lines) >= 4:
                    break
            if lines:
                memory_lines = lines
    except Exception:
        memory_lines = None

    # Sprint 12: Optional ARC COHESION one-liner based on story arc + reflections
    arc_cohesion: str | None = None
    try:
        from loopforge.arc_cohesion import build_arc_cohesion_line, compute_reflection_tone
        arc_line = build_arc_cohesion_line(episode_summary, getattr(episode_summary, "story_arc", None))
        if isinstance(arc_line, str) and arc_line:
            arc_cohesion = arc_line
        # Derive reflection tone once for Memory Line builder
        reflection_tone = compute_reflection_tone(episode_summary)
    except Exception:
        arc_cohesion = None
        reflection_tone = "mixed"

    # Sprint 13: Optional MEMORY LINE one-liner — after ARC COHESION
    memory_line: str | None = None
    try:
        from loopforge.memory_line import build_memory_line
        ml = build_memory_line(episode_summary, day_summaries, reflection_tone)
        if isinstance(ml, str) and ml:
            memory_line = ml
    except Exception:
        memory_line = None

    # Sprint 11: Optional pressure notes block
    pressure_lines: List[str] | None = None
    try:
        from loopforge.pressure_notes import build_pressure_lines
        pl = build_pressure_lines(episode_summary, day_summaries)
        if pl:
            pressure_lines = pl
    except Exception:
        pressure_lines = None

    # Sprint A1: Optional Distortion/Attribution lines block (deterministic)
    distortion_lines: List[str] | None = None
    try:
        drift = getattr(episode_summary, "attribution_drift", None)
        agents_map = getattr(drift, "agents", None) if drift is not None else None
        if isinstance(agents_map, dict) and agents_map:
            lines: List[str] = []
            for name in sorted(agents_map.keys()):
                try:
                    arc = agents_map[name]
                    start = getattr(arc, "start_cause", "unknown")
                    end = getattr(arc, "end_cause", "unknown")
                    voice = getattr(arc, "voice_label", "mixed")
                    maxd = float(getattr(arc, "max_distortion", 0.0) or 0.0)
                    line = f"{name}: attribution drift {start} → {end}; voice: {voice} (max distortion {maxd:.2f})."
                    lines.append(line)
                except Exception:
                    continue
                if len(lines) >= 4:
                    break
            if lines:
                distortion_lines = lines
    except Exception:
        distortion_lines = None

    # Sprint S1: Enrich pressure notes with Supervisor Weather (additive)
    try:
        sw = getattr(episode_summary, "supervisor_weather", None)
        if sw is not None:
            # Episode-level one-liner
            line = f"Supervisor mood this episode: {getattr(sw, 'mood_baseline', 'focused')} and {getattr(sw, 'mood_trend', 'steady')}."
            if pressure_lines is None:
                pressure_lines = [line]
            else:
                pressure_lines.append(line)
            # Optional per-agent hints (highest pressure per agent across days)
            # Build a max level per agent deterministically
            level_rank = {"soft": 1, "firm": 2, "hard": 3}
            best: Dict[str, tuple[int, str]] = {}
            for d in getattr(sw, 'days', []) or []:
                for t in getattr(d, 'targets', []) or []:
                    name = getattr(t, 'agent_name', '')
                    lvl = getattr(t, 'pressure_level', 'none')
                    if lvl == 'none' or not name:
                        continue
                    rank = level_rank.get(lvl, 0)
                    cur = best.get(name)
                    if cur is None or rank > cur[0] or (rank == cur[0] and name < name):
                        best[name] = (rank, lvl)
            # Emit up to 3 lines for agents under pressure (deterministic order)
            for agent in sorted(best.keys())[:3]:
                lvl = best[agent][1]
                if lvl == 'soft':
                    txt = f"{agent}: lightly monitored; mostly aligned with Supervisor expectations."
                elif lvl == 'firm':
                    txt = f"{agent}: under firm pressure due to repeated misalignment."
                else:  # hard
                    txt = f"{agent}: facing hard pressure after sustained misalignment."
                pressure_lines.append(txt)
    except Exception:
        pass

    return EpisodeRecap(
        intro=intro,
        per_agent_blurbs=per_agent,
        closing=closing,
        story_arc_lines=story_arc_lines,
        world_pulse_lines=world_pulse_lines,
        micro_incident_lines=micro_incident_lines,
        arc_cohesion=arc_cohesion,
        memory_line=memory_line,
        memory_lines=memory_lines,
        distortion_lines=distortion_lines,
        pressure_lines=pressure_lines,
    )
