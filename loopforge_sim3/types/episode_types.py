"""
Sim3 Episode Types (Era III)
============================

Defines the final UI-facing episode structures:

    - EpisodeMeta: identity + timing for an episode
    - EpisodeMood: high-level emotional arc
    - StageEpisodeV2: full output consumed by the frontend

These types represent the *final shaped output* of the entire simulation run.

They are produced exclusively by:
    episode/episode_builder.py

They contain:
    - world snapshot (WorldSnapshot)
    - cast sheets (AgentCharacterSheet)
    - day structures (DayWithScenes)
    - episode metadata and mood
    - tension trend for ribbon-style UI graphs

This module has NO simulation logic and NO trace-level data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict

from loopforge_sim3.types.world_types import WorldSnapshot
from loopforge_sim3.types.identity_types import AgentCharacterSheet
from loopforge_sim3.types.event_types import DayWithScenes, EpisodeMood


# ============================================================================
# Episode Metadata
# ============================================================================

@dataclass(frozen=True)
class EpisodeMeta:
    """
    High-level metadata for a single episode:

        - episode id
        - run id (if multi-episode)
        - index within run
        - scenario info
        - timing information (start time, ticks)

    Stored in StageEpisodeV2.episode.
    """

    id: str                       # "ep-001"
    runId: str                    # "run-001"
    index: int                    # 0-based index of this episode within the run

    stageVersion: int             # version of StageEpisodeV2 spec
    scenarioId: str               # scenario configuration id
    scenarioName: str             # human-readable scenario name

    startedAt: Optional[str] = None   # ISO timestamp
    totalTicks: Optional[int] = None  # total ticks in the episode


# ============================================================================
# EpisodeMood (from event_types)
# ============================================================================
# Re-exported indirectly; no need to redefine here.
# Included inside StageEpisodeV2 as a top-level field.


# ============================================================================
# StageEpisodeV2 — final UI-facing payload
# ============================================================================

@dataclass(frozen=True)
class StageEpisodeV2:
    """
    The complete UI-facing episode structure required by the frontend.

    Contains:
        - version (string)
        - episode meta block
        - world snapshot (rooms + layout + tension tiers)
        - cast: agent character sheets
        - days: list of DayWithScenes
        - episodeMood: high-level mood arc
        - tensionTrend: flattened tension values per beat/scene/tick

    Optional:
        - traceAnchors: future-proof hook for scrubbable timeline UIs.
    """

    version: str                         # "2"
    episode: EpisodeMeta                 # identity & timing
    world: WorldSnapshot                 # static + dynamic room snapshot
    cast: List[AgentCharacterSheet]      # resolved cast for UI
    days: List[DayWithScenes]            # narrative structure

    episodeMood: EpisodeMood             # UI banner mood arc
    tensionTrend: List[float]            # flattened trend for charts

    # ---- NEW (frontend’s request) -------------------------------------------------
    traceAnchors: Optional[Dict[str, int]] = None
    # Example:
    #   {"firstSceneTick": 12, "climaxTick": 240}
    #
    # This is NOT full trace data.
    # It's simply tiny handles that help the frontend later align
    # scene cards / beat strips / tension graph markers.
    # Era III doesn't use it internally, but it future-proofs Era IV playback.

