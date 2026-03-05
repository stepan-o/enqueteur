"""Inventory substrate components (Sprint 3.5).

L1 inventory substrate for items/tools. Numeric/ID-only; no free-text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..entity import EntityID


# Local aliases for clarity
RoomID = int
ItemID = int


@dataclass
class InventorySubstrate:
    """
    Inventory substrate (L1).

    - items: list of item IDs owned by the agent.
    - equipped_item_ids: subset of items currently equipped.
    """

    items: List[ItemID]
    equipped_item_ids: List[ItemID]


@dataclass
class ItemState:
    """
    Item state substrate (L1).

    - item_id: unique numeric ID for the item.
    - owner_agent_id: optional owning agent.
    - location_room_id: optional room location if in the world.
    - status_code: enum-coded status (IN_INVENTORY, IN_WORLD, EQUIPPED, etc.).
    """

    item_id: ItemID
    owner_agent_id: Optional[EntityID]
    location_room_id: Optional[RoomID]
    status_code: int
