# entity.py
import itertools
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class EntityID:
    """
    A lightweight, immutable wrapper around int IDs.

    Using a dataclass instead of raw ints makes debugging,
    serialization, and editor tooling MUCH cleaner.
    """
    value: int

    def __int__(self):
        return self.value

    def __str__(self):
        return f"Entity({self.value})"

    def __repr__(self):
        return str(self)


class EntityAllocator:
    """
    Allocates stable, integer-based entity IDs.
    Entities do not store data—they are pure identifiers.

    Features:
    - monotonic ID assignment
    - ID recycling (optional)
    - clear link to external engines (Godot)
    - deterministic replay support
    """
    def __init__(self, start_at=1, recycle_ids=False):
        self._gen = itertools.count(start_at)
        self._recycle_ids = recycle_ids
        self._free_ids = []  # for optional reuse

    def create(self) -> EntityID:
        if self._recycle_ids and self._free_ids:
            return EntityID(self._free_ids.pop())

        return EntityID(next(self._gen))

    def destroy(self, ent: EntityID):
        if self._recycle_ids:
            self._free_ids.append(ent.value)
