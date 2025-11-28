from dataclasses import dataclass, field
from typing import List
from ..ecs.entity import EntityID


# ---------------------------------------------------------------------------
# ERA V — ROOM IDENTITY (static metadata)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoomIdentity:
    """
    Immutable identity for a room.

    - id: canonical identifier (used in graphs & snapshots)
    - label: human readable name
    - kind: semantic category (hallway, lab, default, etc.)
    """
    id: str
    label: str
    kind: str = "default"


# ---------------------------------------------------------------------------
# ERA V — ROOM INSTANCE (mutable state)
# ---------------------------------------------------------------------------

@dataclass
class Room:
    """
    Runtime mutable room.
    Holds:
    - identity (static metadata)
    - entities: List[EntityID]
    """

    identity: RoomIdentity
    entities: List[EntityID] = field(default_factory=list)

    def add(self, ent: EntityID):
        if ent not in self.entities:
            self.entities.append(ent)

    def remove(self, ent: EntityID):
        if ent in self.entities:
            self.entities.remove(ent)
