"""Perception & attention substrate components (Sprint 3.2).

These components span L1/L2 (raw perception + attention/salience).
Only numeric / ID data is stored; no semantic labels. Shapes remain
Rust-portable per SOT-SIM4-ECS-SUBSTRATE-COMPONENTS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ..entity import EntityID
from .embodiment import RoomID, AssetID


@dataclass
class PerceptionSubstrate:
    """
    Raw perception substrate (L1/L2).

    Stores which agents, assets, and rooms are currently visible,
    along with proximity scores. All values are numeric or IDs.
    """

    visible_agents: List[EntityID]
    visible_assets: List[AssetID]
    visible_rooms: List[RoomID]
    proximity_scores: Dict[EntityID, float]


@dataclass
class AttentionSlots:
    """
    Attention substrate (L2).

    Tracks focused targets and secondary attention slots,
    plus an overall distraction level.
    """

    focused_agent: Optional[EntityID]
    focused_asset: Optional[AssetID]
    focused_room: Optional[RoomID]
    secondary_targets: List[EntityID]
    distraction_level: float


@dataclass
class SalienceState:
    """
    Salience substrate (L2).

    Numeric salience values for agents, topics, and locations.
    No semantic labels are stored here.
    """

    agent_salience: Dict[EntityID, float]
    topic_salience: Dict[int, float]
    location_salience: Dict[RoomID, float]
