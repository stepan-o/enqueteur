"""
Sim3 Trace Types (Era III)
==========================

Defines the intermediate trace structures emitted during simulation:

    - TickTrace: atomic tick-level record
    - PresenceTrace: agent → room mapping per tick
    - BeatTrace: grouped ticks
    - SceneTrace: grouped beats into narrative units
    - DayTrace: grouped scenes into days

These traces are consumed by:
    - recorder/trace_recorder.py
    - episode/episode_builder.py

No simulation logic lives here.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from legacy.backend.loopforge_sim3.types.world_types import WorldSnapshot
from legacy.backend.loopforge_sim3.types.event_types import TickEvent, BeatMetadata, SceneUnit


# ============================================================================
# 1. TickTrace — atomic per-tick snapshot
# ============================================================================

@dataclass(frozen=True)
class TickTrace:
    """
    The atomic trace emitted each tick.

    Contains:
        - tick index
        - world snapshot
        - agent stress/flags snapshot
        - events emitted at this tick
        - optional controller/debug flags
    """

    tick: int

    # UI-ready dynamic world snapshot (positions, tension, hazards)
    world: WorldSnapshot

    # Per-agent runtime values
    agent_stress: Dict[str, float]
    agent_status: Dict[str, List[str]]
    agent_room: Dict[str, str]

    # Events (from event_types.TickEvent)
    events: List[TickEvent]

    # Arbitrary controller flags / runtime debug info
    meta: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 2. PresenceTrace — NEW (for true agent movement visualization)
# ============================================================================

@dataclass(frozen=True)
class PresenceTrace:
    """
    The distilled agent → room map per tick.

    Used to:
        - draw the live room occupancy map in StageEpisodeV2
        - animate agent transitions between rooms
        - power timeline strips based purely on movement

    It intentionally does NOT include stress, flags, or narrative info.
    Only spatial presence.
    """

    tick: int
    agent_room: Dict[str, str]        # agent_id → room_id


# ============================================================================
# 3. BeatTrace — group of ticks
# ============================================================================

@dataclass(frozen=True)
class BeatTrace:
    """
    A beat is a small cluster of ticks forming a “moment”.

    Includes:
        - beat index
        - tick range
        - metadata derived from BeatMetadata (tension, mood, etc.)
        - the list of contained TickTraces
    """

    beat: int
    start_tick: int
    end_tick: int

    metadata: BeatMetadata
    ticks: List[TickTrace]


# ============================================================================
# 4. SceneTrace — group of beats
# ============================================================================

@dataclass(frozen=True)
class SceneTrace:
    """
    A narrative unit representing a chunk of activity.

    Contains:
        - scene index
        - beats
        - derived SceneUnit metadata (labels, dominant tensions)
        - optional summary strings for UI
    """

    scene: int
    beats: List[BeatTrace]

    descriptor: SceneUnit              # from event_types.SceneUnit
    summary: Optional[str] = None


# ============================================================================
# 5. DayTrace — group of scenes
# ============================================================================

@dataclass(frozen=True)
class DayTrace:
    """
    Represents all narrative output for a single day.

    Includes:
        - day index
        - scenes list
        - aggregated day summary (DaySummary from event_types)
        - optional day-level mood state
    """

    day: int
    scenes: List[SceneTrace]

    # DaySummary includes tension curves, incident counts, etc.
    summary: Any                       # usually DaySummary
    mood: Optional[str] = None         # EpisodeMood, but loose for now
