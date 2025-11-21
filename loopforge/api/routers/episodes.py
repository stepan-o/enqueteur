from __future__ import annotations

from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException

import loopforge.analytics.run_registry as run_registry
from loopforge.analytics.run_registry import EpisodeRecord
import loopforge.analytics.analysis_api as analysis_api
from loopforge.stage import build_stage_episode
from loopforge.narrative.characters import CHARACTERS

router = APIRouter(tags=["episodes"])

# Default locations; can be parameterized in future phases
DEFAULT_ACTION_LOG = Path("logs/loopforge_actions.jsonl")
DEFAULT_SUPERVISOR_LOG = None  # Optional; None by default per phase constraints


def _find_latest_by_episode_id(records: List[EpisodeRecord], episode_id: str) -> Optional[EpisodeRecord]:
    match: Optional[EpisodeRecord] = None
    for r in records:
        try:
            if getattr(r, "episode_id", None) == episode_id:
                match = r
        except Exception:
            continue
    return match


@router.get("/episodes")
def list_episodes() -> List[Dict[str, Any]]:
    """List known episodes from the append-only run registry (read-only)."""
    rows = run_registry.load_registry()
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "episode_id": r.episode_id,
                "run_id": r.run_id,
                "episode_index": int(getattr(r, "episode_index", 0) or 0),
                "days": int(getattr(r, "days", 0) or 0),
                "created_at": str(getattr(r, "created_at", "")),
            }
        )
    return out


@router.get("/episodes/{episode_id}")
def get_episode(episode_id: str) -> Dict[str, Any]:
    """Return a fully built StageEpisode JSON for the latest record with this episode_id.

    This endpoint is read-only and operates on the registry → analysis → builder path.
    """
    records = run_registry.load_registry()
    rec = _find_latest_by_episode_id(records, episode_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Episode not found")

    # Analyze to rebuild EpisodeSummary and DaySummary slice
    ep = analysis_api.analyze_episode_from_record(
        rec,
        action_log_path=DEFAULT_ACTION_LOG,
        supervisor_log_path=DEFAULT_SUPERVISOR_LOG,
    )

    # Build StageEpisode using canonical sources; pass through story_arc/long_memory if present
    stage_ep = build_stage_episode(
        episode_summary=ep,
        day_summaries=ep.days,
        story_arc=getattr(ep, "story_arc", None),
        long_memory=getattr(ep, "long_memory", None),
        character_defs=CHARACTERS,
        include_narrative=True,
    )
    return stage_ep.to_dict()


@router.get("/episodes/{episode_id}/raw")
def get_episode_raw(episode_id: str) -> Dict[str, Any]:
    """Return the raw export (EpisodeSummary) dict for debugging.

    This is optional and intended for development only; still read-only.
    """
    records = run_registry.load_registry()
    rec = _find_latest_by_episode_id(records, episode_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Episode not found")

    ep = analysis_api.analyze_episode_from_record(
        rec,
        action_log_path=DEFAULT_ACTION_LOG,
        supervisor_log_path=DEFAULT_SUPERVISOR_LOG,
    )
    return analysis_api.episode_summary_to_dict(ep)
