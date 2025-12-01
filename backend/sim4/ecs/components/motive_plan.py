"""Motive & plan substrate components (Sprint 3.4).

These components live primarily in mind layer L5 (motives & planning).
All fields are numeric/ID-only and Rust-portable per SOT-SIM4-ECS-SUBSTRATE-COMPONENTS.
Systems are responsible for invariants such as list length alignment; the
dataclasses here are passive storage only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..entity import EntityID

# Local ID aliases (numeric, Rust-portable)
RoomID = int
AssetID = int


@dataclass
class MotiveSubstrate:
    """
    Motive substrate (L5).

    - active_motives: hashed motive IDs (e.g. encoded as ints).
    - motive_strengths: numeric strength per motive, same logical length as active_motives.
      NOTE: The dataclass does NOT enforce alignment; systems must keep lists in sync.
    - last_update_tick: tick index when motives were last updated.
    """

    active_motives: List[int]
    motive_strengths: List[float]
    last_update_tick: int


@dataclass
class PlanStepSubstrate:
    """
    Single structural plan step (L5).

    - step_id: hashed step code (int).
    - target_agent_id / target_room_id / target_asset_id: optional numeric IDs.
    - status_code: enum-coded status (PENDING, IN_PROGRESS, DONE, FAILED, etc.), as an int.
    """

    step_id: int
    target_agent_id: Optional[EntityID]
    target_room_id: Optional[RoomID]
    target_asset_id: Optional[AssetID]
    status_code: int


@dataclass
class PlanLayerSubstrate:
    """
    Plan layer substrate (L5).

    - steps: ordered list of PlanStepSubstrate representing the current plan.
    - current_index: index into `steps` for the active step.
    - plan_confidence: numeric confidence level in the current plan.
    - revision_needed: flag indicating whether plan revision is requested.
    """

    steps: List[PlanStepSubstrate]
    current_index: int
    plan_confidence: float
    revision_needed: bool
