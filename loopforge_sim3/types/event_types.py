"""
Sim3 Event & Time Types (Era III)
=================================

Defines the complete temporal identity layer:
- TickEvent: atomic event emitted each tick
- BeatMetadata: coarse grouping of ticks
- SceneUnit: significant narrative moment derived from beats
- DaySummary: aggregated metadata for a day
- DayWithScenes: DaySummary + ordered list of scenes
- EpisodeMood: overall episode arc (for StageEpisodeV2.banner)

These structures are *data-only* and used by:
    sim/event_emitter.py
    sim/beat_engine.py
    sim/scene_trigger.py
    sim/day_engine.py
    recorder/trace_recorder.py
    episode/episode_builder.py

They form the spine of the Era III “tick → beat → scene → day”
time model required to build StageEpisodeV2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal


# ---------------------------------------------------------------------------
# Shared enums / literals
# ---------------------------------------------------------------------------

TensionTier = Literal["low", "medium", "high", "critical"]


# ---------------------------------------------------------------------------
# A. TickEvent — atomic event emitted every tick
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TickEvent:
    """
    Atomic per-tick event emitted by the sim.

    A TickEvent captures:
        - tick index
        - world/room truth snapshot
        - per-agent micro activity
        - tension calculation
        - narrative triggers (faults, arrivals, messages)

    TraceRecorder stores these raw events for SceneExtraction and Day summaries.
    """

    tick: int                          # absolute tick number in episode

    # Where the agent(s) are — backend uses this in scene extraction
    room_by_agent: Dict[str, str]      # agent_id → room_id

    # Per-agent state deltas
    agent_tension: Dict[str, float]    # agent_id → tension (0–1)
    agent_flags: Dict[str, List[str]]  # narrative flags like ["fault", "handoff"]

    # Supervisor activity proxy (0–1)
    supervisor_activity: float

    # World-level tension reading
    world_tension: float               # 0–1

    # Raw event tags for scene extraction: ["arrival", "fault", "transition"]
    event_tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# B. BeatMetadata — grouping of ticks into “moments”
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BeatMetadata:
    """
    One beat combines:
        - many TickEvents
        - derived tension summary
        - room focal point
        - agents involved
        - narrative tags from ticks

    Beats are NOT shown to UI directly — they are input into SceneTrigger.
    """

    index: int                         # beat index (monotonic)
    ticks: List[TickEvent]             # raw ticks inside this beat

    # Derived properties
    timeCode: int                      # representative tick index
    mainRoomId: str                    # room of focal activity
    involvedAgents: List[str]

    tensionScore: float                # 0–1
    tensionTier: TensionTier
    eventTags: List[str]               # aggregated from constituent ticks


# ---------------------------------------------------------------------------
# C. SceneUnit — significant moment extracted from beats
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SceneUnit:
    """
    A key narrative/functional moment in the story.

    Derived from beats that cross significance thresholds (faults, tension spike,
    room transition, etc.), or beats merged by scene-trigger logic.

    Directly used by StageEpisodeV2.
    """

    id: str                            # "d1-s0"
    dayIndex: int
    index: int                         # order within the day

    timeCode: int                      # tick number representing the scene

    mainRoomId: str
    involvedAgents: List[str]

    tensionTier: TensionTier
    tensionDelta: Optional[float]      # signed delta from previous scene/day

    summary: str
    narrativeTags: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# D. DaySummary — aggregate narrative + functional metadata for a day
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DaySummary:
    """
    Aggregated summary used for:
        - Day storyboard tiles
        - Tension strips
        - Supervisor activity graphs
        - Primary room + dominant agents
        - 1–2 sentence day summary
    """

    index: int                         # day index
    label: str                         # "Day 1"

    tensionScore: float                # averaged or weighted tension
    tensionTier: TensionTier

    primaryRoomId: str                 # dominant room of the day
    totalIncidents: int                # count of notable events
    supervisorActivity: float          # 0–1 proxy

    dominantAgents: List[str]          # 1–3 key agents
    summary: str                       # 1–2 sentences


# ---------------------------------------------------------------------------
# E. DayWithScenes — DaySummary + Ordered SceneUnits
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DayWithScenes(DaySummary):
    """
    Full day payload for StageEpisodeV2:
    - summary metadata
    - ordered list of SceneUnit[]
    """

    scenes: List[SceneUnit]


# ---------------------------------------------------------------------------
# F. EpisodeMood — for StageEpisodeV2 “banner”
# ---------------------------------------------------------------------------

EpisodeMoodTier = Literal["calm", "rising", "volatile", "decompression"]

@dataclass(frozen=True)
class EpisodeMood:
    """
    Episode-level mood arc computation:
        - calm
        - rising
        - volatile
        - decompression

    Used for the UI top banner.
    """

    tier: EpisodeMoodTier
    summary: str
    dominantColor: Optional[str] = None
