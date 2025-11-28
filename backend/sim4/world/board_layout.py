# backend/sim4/world/board_layout.py

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ConnectionSpec:
    """
    Immutable definition of how rooms are connected in the static world:

    - cost: movement cost
    - kind: hallway, door, ladder, elevator, etc.
    """
    to: str
    cost: float = 1.0
    kind: str = "hallway"


@dataclass(frozen=True)
class BoardLayoutSpec:
    """
    AAA Era V — static layout of the world.

    This is consumed by:
        - Pathfinding systems
        - Navigation LLM reasoning
        - Snapshot + episode builders
        - World bootstrap

    Keys:
        rooms:        list of all room IDs
        connections:  adjacency list mapping room → [ConnectionSpec]
    """
    rooms: List[str]
    connections: Dict[str, List[ConnectionSpec]] = field(default_factory=dict)

    def neighbors(self, room_id: str) -> List[ConnectionSpec]:
        """Return static adjacency list for a room."""
        return self.connections.get(room_id, [])
