from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Optional, Dict, List, Any, DefaultDict
from collections import defaultdict, Counter

from .day_runner import compute_day_summary
from .reporting import summarize_episode, EpisodeSummary, DaySummary, AgentEpisodeStats, AgentDayStats
from .supervisor_activity import compute_supervisor_activity
from .logging_utils import read_action_log_entries, read_action_log_entries_for_episode


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

    # Load only matching entries (raw dicts)
    entries = read_action_log_entries_for_episode(
        action_log_path,
        run_id=str(run_id),
        episode_id=str(episode_id),
    )
    if not entries:
        raise ValueError(f"No action log entries found for run_id={run_id} and episode_id={episode_id}.")

    supervisor_by_day: Dict[int, List[dict]] = {}
    if supervisor_log_path is not None:
        sup_rows = _read_supervisor_jsonl(supervisor_log_path)
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
            entries=entries,
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

    return out
