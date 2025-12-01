"""Intent & action substrate components (Sprint 3.5).

These components encode numeric intent and action substrate bridging L1/L5.
No semantics or free-text, just numeric codes and IDs. Systems interpret the
codes; narrative interprets meanings. Shapes are Rust-portable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from ..entity import EntityID


# Local numeric aliases for IDs used by intents/actions
RoomID = int
AssetID = int


@dataclass
class PrimitiveIntent:
    """
    Primitive intent substrate (L5 input).

    - intent_code: hashed intent ID (e.g. "want_to_talk_to_X" as an int).
    - target_*_id: optional numeric targets.
    - priority: numeric priority scalar.
    """

    intent_code: int
    target_agent_id: Optional[EntityID]
    target_room_id: Optional[RoomID]
    target_asset_id: Optional[AssetID]
    priority: float


@dataclass
class SanitizedIntent:
    """
    Sanitized intent substrate (L5).

    Same shape as PrimitiveIntent plus:
    - valid: whether intent is allowed/feasible.
    - reason_code: enum-coded reason (0=OK, other values = rejection reasons).
    """

    intent_code: int
    target_agent_id: Optional[EntityID]
    target_room_id: Optional[RoomID]
    target_asset_id: Optional[AssetID]
    priority: float
    valid: bool
    reason_code: int


@dataclass
class MovementIntent:
    """
    Movement intent substrate (L1/L5 bridge).

    - kind_code: enum-coded movement type.
    - target_room_id: target room (if room-based).
    - target_position: (x, y) float coordinates, or None.
    - follow_agent_id: agent to follow, if any.
    - speed_scalar: movement speed multiplier.
    - active: whether this movement intent is currently active.
    """

    kind_code: int
    target_room_id: Optional[RoomID]
    target_position: Optional[Tuple[float, float]]
    follow_agent_id: Optional[EntityID]
    speed_scalar: float
    active: bool


@dataclass
class InteractionIntent:
    """
    Interaction intent substrate (L1/L5 bridge).

    - kind_code: enum-coded interaction type.
    - target_agent_id / target_asset_id: optional targets.
    - strength_scalar: numeric intensity.
    - active: whether this interaction intent is active.
    """

    kind_code: int
    target_agent_id: Optional[EntityID]
    target_asset_id: Optional[AssetID]
    strength_scalar: float
    active: bool


@dataclass
class ActionState:
    """
    Action state substrate (L1/L5).

    - mode_code: enum-coded mode (IDLE, WALKING, TALKING, etc.) as an int.
    - time_in_mode: accumulated time in current mode.
    - last_mode_change_tick: tick index when the mode last changed.
    """

    mode_code: int
    time_in_mode: float
    last_mode_change_tick: int
