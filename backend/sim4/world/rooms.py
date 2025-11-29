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

    - id: canonical room ID (A, B, etc.)
    - label: human-readable name
    - kind: semantic classification (hallway, lab, default...)
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
    Runtime room container.

    Fields:
    - room_id: canonical ID string (duplicated from identity.id for fast lookup)
    - identity: immutable metadata
    - entities: list of EntityID currently in room
    """

    room_id: str
    identity: RoomIdentity
    entities: List[EntityID] = field(default_factory=list)

    def add(self, ent: EntityID):
        if ent not in self.entities:
            self.entities.append(ent)

    def remove(self, ent: EntityID):
        if ent in self.entities:
            self.entities.remove(ent)
