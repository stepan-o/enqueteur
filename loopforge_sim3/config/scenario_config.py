"""
Sim3 Scenario Configuration
==========================

Defines the canonical ScenarioConfig used by the Sim3 runner, backend logic,
and the StageEpisode builder for Era III.

This module is intentionally minimal:
- ScenarioConfig selects *which* world to load from the world registry
- ScenarioConfig selects *which* cast to use from the narrative registry
- ScenarioConfig defines temporal parameters for simulation playback
- No world layout data lives here
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Backend source of truth for world definitions
from loopforge_sim3.world.world_registry import WORLD_LAYOUTS

# Cast source of truth (Sim3 will use this for character sheets)
from loopforge.narrative.characters import CHARACTERS


# ---------------------------------------------------------------------------
# Basic constants
# ---------------------------------------------------------------------------

DEFAULT_WORLD_ID = "factory_floor_v1"
MIN_CAST_SIZE = 2


# ---------------------------------------------------------------------------
# ScenarioConfig
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScenarioConfig:
    """
    Canonical configuration object for running a Sim3 scenario.

    This object:
    - selects the world layout (via world_id)
    - selects cast mode ("default" uses full registry; "custom" uses provided list)
    - defines temporal parameters for the simulation
    - is frozen/immutable for safe propagation across the Sim stack

    It is consumed by:
    - Sim3 runner
    - EpisodeBuilder (Sim3 → StageEpisode v2)
    - Future ScenarioMeta module (Sim3 metadata layer)
    """

    # -------------------------
    # Public configuration
    # -------------------------

    # world selection
    world_id: str = DEFAULT_WORLD_ID

    # cast selection mode
    cast_mode: str = "default"     # "default" | "custom"
    custom_cast: Optional[List[str]] = None

    # simulation temporal parameters
    tick_resolution: str = "normal"   # "normal" | "fine"
    ticks_per_day: int = 8
    episode_length_days: int = 3

    # -------------------------
    # Derived / internal fields
    # -------------------------

    world_spec: dict = field(init=False)
    cast: List[str] = field(init=False)

    # -------------------------
    # Validation + derivation
    # -------------------------

    def __post_init__(self):
        # -------------------------
        # 1. Validate world
        # -------------------------
        if self.world_id not in WORLD_LAYOUTS:
            raise ValueError(f"Unknown world_id: {self.world_id}")

        object.__setattr__(self, "world_spec", WORLD_LAYOUTS[self.world_id])

        # -------------------------
        # 2. Temporal validation
        # -------------------------
        if self.ticks_per_day < 1:
            raise ValueError("ticks_per_day must be >= 1")

        if self.episode_length_days < 1:
            raise ValueError("episode_length_days must be >= 1")

        # -------------------------
        # 3. Cast mode validation
        # -------------------------
        if self.cast_mode not in ("default", "custom"):
            raise ValueError(f"Invalid cast_mode: {self.cast_mode}")

        # -------------------------
        # 4. Cast selection
        # -------------------------
        if self.cast_mode == "default":
            cast_list = list(CHARACTERS.keys())

        else:
            if not self.custom_cast:
                raise ValueError("custom_cast must be provided when cast_mode='custom'")

            # validate characters
            for name in self.custom_cast:
                if name not in CHARACTERS:
                    # tests expect plural phrase “Unknown characters”
                    raise ValueError(f"Unknown characters: {name}")

            if len(self.custom_cast) < MIN_CAST_SIZE:
                # tests expect exact substring
                raise ValueError("Cast size too small")

            cast_list = list(self.custom_cast)

        object.__setattr__(self, "cast", cast_list)


# ---------------------------------------------------------------------------
# Factory helper for convenience
# ---------------------------------------------------------------------------

def make_scenario(
        *,
        world_id: str = DEFAULT_WORLD_ID,
        cast_mode: str = "default",
        custom_cast: Optional[List[str]] = None,
        tick_resolution: str = "normal",
        ticks_per_day: int = 8,
        episode_length_days: int = 3,
) -> ScenarioConfig:
    """
    Thin wrapper around ScenarioConfig useful for callers that prefer kwargs.
    """
    return ScenarioConfig(
        world_id=world_id,
        cast_mode=cast_mode,
        custom_cast=custom_cast,
        tick_resolution=tick_resolution,
        ticks_per_day=ticks_per_day,
        episode_length_days=episode_length_days,
    )
