from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Optional, Dict, List, Any, DefaultDict
from collections import defaultdict, Counter

from .day_runner import compute_day_summary
from .reporting import summarize_episode, EpisodeSummary, DaySummary, AgentEpisodeStats, AgentDayStats
from .supervisor_activity import compute_supervisor_activity
from .logging_utils import read_action_log_entries
from .run_registry import EpisodeRecord
from pathlib import Path as _P


def _read_supervisor_jsonl(path: Path) -> List[dict]:
    """Fail-soft reader for supervisor JSONL.

    Returns list of dicts. If file is missing or malformed, returns [].
    We intentionally avoid constructing strong types — for activity we only
    need day grouping and counting.
    """
    p = Path(path)
    if not p or not p.exists():
        return []
    rows: List[dict] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    # skip malformed line
                    continue
    except Exception:
        return rows
    return rows


def _group_supervisor_by_day(rows: List[dict], steps_per_day: int) -> Dict[int, List[dict]]:
    by_day: DefaultDict[int, List[dict]] = defaultdict(list)
    for r in rows:
        day_idx = None
        if isinstance(r, dict):
            if "day_index" in r and isinstance(r["day_index"], int):
                day_idx = r["day_index"]
            elif "step" in r:
                try:
                    step_val = int(r["step"]) if r["step"] is not None else 0
                except Exception:
                    step_val = 0
                day_idx = step_val // max(1, int(steps_per_day))
        if day_idx is None:
            day_idx = 0
        by_day[day_idx].append(r)
    return dict(by_day)


def _read_action_jsonl_raw(path: Path) -> List[dict]:
    """Read the action JSONL file and return a list of raw dict rows.

    - Skips empty/malformed lines (fail-soft)
    - Does not coerce into strong types; callers decide how to interpret
    """
    p = Path(path)
    if not p.exists():
        return []
    rows: List[dict] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except Exception:
        return rows
    return rows


def analyze_episode(
    action_log_path: Path,
    *,
    supervisor_log_path: Optional[Path] = None,
    steps_per_day: int = 50,
    days: int = 3,
    episode_id: Optional[str] = None,
    run_id: Optional[str] = None,
    episode_index: int = 0,
) -> EpisodeSummary:
    """
    High-level entrypoint.
    Loads logs, computes DaySummary for each day from the slice that matches
    the provided (run_id, episode_id), applies supervisor activity if provided,
    and returns EpisodeSummary.

    Sprint E4: analysis is ID-driven only. ID-less logs are not supported.
    """
    # Enforce IDs for analysis
    if not run_id or not episode_id:
        raise ValueError("analyze_episode requires run_id and episode_id; ID-less logs are no longer supported.")

    # Load full file as raw rows, enforce identity presence on every row
    all_rows = _read_action_jsonl_raw(action_log_path)
    if any(("run_id" not in r or "episode_id" not in r) for r in all_rows):
        raise ValueError("Action log contains rows without identity fields; analyze_episode now requires IDs on all rows.")

    # Filter strictly by (run_id, episode_id)
    rows = [r for r in all_rows if r.get("run_id") == run_id and r.get("episode_id") == episode_id]
    if not rows:
        raise ValueError(f"No action log entries found for run_id={run_id} and episode_id={episode_id}.")

    # Sort by step ascending (missing/invalid treated as 0)
    def _step_key(d: dict) -> int:
        try:
            return int(d.get("step", 0) or 0)
        except Exception:
            return 0
    rows.sort(key=_step_key)

    supervisor_by_day: Dict[int, List[dict]] = {}
    if supervisor_log_path is not None:
        sup_rows = _read_supervisor_jsonl(supervisor_log_path)
        # Sprint E6: supervisor logs must be ID-aware and strictly filtered
        # Validate all rows have identity fields; ID-less supervisor logs are no longer supported.
        missing_id = [r for r in sup_rows if not (isinstance(r, dict) and all(k in r for k in ("run_id", "episode_id", "episode_index")))]
        if missing_id:
            raise ValueError("Supervisor log entry missing run_id/episode_id")
        # Filter to matching run/episode; ignore others
        sup_rows = [r for r in sup_rows if r.get("run_id") == run_id and r.get("episode_id") == episode_id]
        supervisor_by_day = _group_supervisor_by_day(sup_rows, steps_per_day)

    day_summaries: List[DaySummary] = []
    prev_stats: Optional[Dict[str, AgentDayStats]] = None

    for day_index in range(days):
        sup_rows_for_day = supervisor_by_day.get(day_index, [])
        # For activity, only the count matters
        supervisor_activity = compute_supervisor_activity(sup_rows_for_day, steps_per_day)
        ds = compute_day_summary(
            day_index=day_index,
            action_log_path=action_log_path,
            steps_per_day=steps_per_day,
            previous_day_stats=prev_stats,
            supervisor_activity=supervisor_activity,
            entries=rows,
        )
        day_summaries.append(ds)
        prev_stats = ds.agent_stats

    # Thread identity (already provided, do not generate fallbacks)
    return summarize_episode(
        day_summaries,
        episode_id=str(episode_id),
        run_id=str(run_id),
        episode_index=int(episode_index or 0),
    )


def _dataclass_to_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    return obj


def analyze_episode_from_record(
    record: EpisodeRecord,
    *,
    action_log_path: Path,
    supervisor_log_path: Optional[Path] = None,
) -> EpisodeSummary:
    """Thin adapter: EpisodeRecord -> analyze_episode call.

    Validates presence of required fields on the record and invokes
    analyze_episode with those values. This is above-the-seam and read-only.
    """
    if record is None:
        raise ValueError("EpisodeRecord is required")
    # Validate required fields
    rid = getattr(record, "run_id", None)
    eid = getattr(record, "episode_id", None)
    eidx = getattr(record, "episode_index", None)
    spd = getattr(record, "steps_per_day", None)
    ndays = getattr(record, "days", None)
    if not rid or not eid:
        raise ValueError("EpisodeRecord missing run_id or episode_id")
    if eidx is None:
        eidx = 0
    if not isinstance(spd, int) or not isinstance(ndays, int):
        raise ValueError("EpisodeRecord missing steps_per_day or days")

    return analyze_episode(
        action_log_path=action_log_path,
        supervisor_log_path=supervisor_log_path,
        steps_per_day=int(spd),
        days=int(ndays),
        episode_id=str(eid),
        run_id=str(rid),
        episode_index=int(eidx),
    )


def episode_summary_to_dict(summary: EpisodeSummary) -> dict:
    """Produce a JSON-serializable dictionary for EpisodeSummary.

    - Uses dataclasses.asdict for simple dataclasses
    - Builds derived per-agent blame timeline and counts from DaySummary.belief_attributions
    - Ensures no non-serializable objects remain
    """
    # Base structure
    out: Dict[str, Any] = {
        "run_id": getattr(summary, "run_id", None),
        "episode_id": getattr(summary, "episode_id", None),
        "episode_index": getattr(summary, "episode_index", 0),
        "days": [],
        "agents": {},
        "tension_trend": list(summary.tension_trend or []),
    }

    # Serialize days minimally with agent stats and attribution presence
    for d in summary.days:
        day_block: Dict[str, Any] = {
            "day_index": d.day_index,
            "perception_mode": getattr(d, "perception_mode", "accurate"),
            "tension_score": getattr(d, "tension_score", 0.0),
            "total_incidents": getattr(d, "total_incidents", 0),
            "agents": {},
        }
        for name, s in (d.agent_stats or {}).items():
            day_block["agents"][name] = {
                "role": s.role,
                "guardrail_count": int(s.guardrail_count),
                "context_count": int(s.context_count),
                "avg_stress": float(s.avg_stress),
            }
        out["days"].append(day_block)

    # Serialize episode agent aggregates
    for name, a in (summary.agents or {}).items():
        # Avoid embedding potentially complex reflection objects; stick to numeric/text fields
        out["agents"][name] = {
            "name": a.name,
            "role": a.role,
            "guardrail_total": int(a.guardrail_total),
            "context_total": int(a.context_total),
            "trait_deltas": dict(a.trait_deltas or {}),
            "stress_start": a.stress_start if a.stress_start is not None else None,
            "stress_end": a.stress_end if a.stress_end is not None else None,
            "visual": a.visual,
            "vibe": a.vibe,
            "tagline": a.tagline,
            "trait_snapshot": (dict(a.trait_snapshot) if isinstance(getattr(a, "trait_snapshot", None), dict) else (a.trait_snapshot if getattr(a, "trait_snapshot", None) is None else None)),
        }

    # Derived blame timeline and counts per agent
    # Build a set of agent names across all days from stats to ensure even absent attribution still yields empty lists
    agent_names = set(summary.agents.keys())
    for d in summary.days:
        agent_names.update((d.agent_stats or {}).keys())
    for name in sorted(agent_names):
        timeline: List[str] = []
        for d in summary.days:
            attr_map = getattr(d, "belief_attributions", {}) or {}
            cause = None
            if name in attr_map and getattr(attr_map[name], "cause", None):
                cause = attr_map[name].cause
            timeline.append(cause or "unknown")
        counts = Counter(timeline)
        # Ensure all keys exist
        blame_counts = {
            "random": int(counts.get("random", 0)),
            "system": int(counts.get("system", 0)),
            "supervisor": int(counts.get("supervisor", 0)),
            "self": int(counts.get("self", 0)),
            "unknown": int(counts.get("unknown", 0)),
        }
        out.setdefault("agents", {}).setdefault(name, {})
        out["agents"][name]["blame_timeline"] = timeline
        out["agents"][name]["blame_counts"] = blame_counts

    # Sprint 8: Optional story arc block (additive)
    try:
        arc = getattr(summary, "story_arc", None)
        out["story_arc"] = arc.to_dict() if arc is not None else None
    except Exception:
        out["story_arc"] = None

    # Sprint 10: Optional long memory block (additive)
    try:
        lm = getattr(summary, "long_memory", None)
        if isinstance(lm, dict):
            out["long_memory"] = {name: mem.to_dict() for name, mem in lm.items()} if lm else {}
            if not lm:
                out["long_memory"] = None
        else:
            out["long_memory"] = None
    except Exception:
        out["long_memory"] = None

    # Sprint A0: Optional world pulse history (additive)
    try:
        wph = getattr(summary, "world_pulse_history", None)
        if isinstance(wph, list) and wph:
            out["world_pulse_history"] = list(wph)
        else:
            out["world_pulse_history"] = None
    except Exception:
        out["world_pulse_history"] = None

    # Sprint N2 (optional): micro-incidents export (fail-soft)
    try:
        from .micro_incidents import build_micro_incidents
        incidents = build_micro_incidents(summary)
        out["micro_incidents"] = [
            {
                "day_index": mi.day_index,
                "incident_type": mi.incident_type,
                "severity": mi.severity,
                "agents_involved": list(mi.agents_involved),
                "summary": mi.summary,
            }
            for mi in incidents
        ] if incidents else []
    except Exception:
        # Do not fail export if micro_incidents module or inputs are missing
        pass

    # Sprint S1: supervisor_weather export (fail-soft)
    try:
        sw = getattr(summary, "supervisor_weather", None)
        if sw is not None:
            out["supervisor_weather"] = {
                "mood_baseline": getattr(sw, "mood_baseline", None),
                "mood_trend": getattr(sw, "mood_trend", None),
                "days": [
                    {
                        "day_index": getattr(d, "day_index", 0),
                        "mood": getattr(d, "mood", None),
                        "tone_volatility": getattr(d, "tone_volatility", None),
                        "global_pressure": getattr(d, "global_pressure", None),
                        "alignment_score": float(getattr(d, "alignment_score", 0.0) or 0.0),
                        "targets": [
                            {
                                "agent_name": getattr(t, "agent_name", None),
                                "pressure_level": getattr(t, "pressure_level", None),
                                "reason": getattr(t, "reason", None),
                                "misalignment_score": float(getattr(t, "misalignment_score", 0.0) or 0.0),
                            }
                            for t in (getattr(d, "targets", []) or [])
                        ],
                    }
                    for d in (getattr(sw, "days", []) or [])
                ],
            }
    except Exception:
        pass

    # Sprint A1: attribution_drift export (fail-soft)
    try:
        drift = getattr(summary, "attribution_drift", None)
        agents_map = getattr(drift, "agents", None) if drift is not None else None
        if isinstance(agents_map, dict):
            out["attribution_drift"] = {
                name: {
                    "start_cause": getattr(arc, "start_cause", None),
                    "end_cause": getattr(arc, "end_cause", None),
                    "max_distortion": float(getattr(arc, "max_distortion", 0.0) or 0.0),
                    "voice_label": getattr(arc, "voice_label", None),
                    "days": [
                        {
                            "day_index": int(getattr(s, "day_index", 0) or 0),
                            "base_cause": getattr(s, "base_cause", None),
                            "distorted_cause": getattr(s, "distorted_cause", None),
                            "distortion_level": float(getattr(s, "distortion_level", 0.0) or 0.0),
                            "drivers": list(getattr(s, "drivers", []) or []),
                        }
                        for s in (getattr(arc, "days", []) or [])
                    ],
                }
                for name, arc in agents_map.items()
            }
    except Exception:
        pass

    return out
