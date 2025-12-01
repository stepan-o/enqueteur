from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Set, List

# Rust-portable alias: entity identifiers are represented as small positive ints
EntityID = int


@dataclass
class EntityAllocator:
    """
    Deterministic allocator for EntityID values.

    - IDs are small positive integers (>= 1) by default.
    - Allocation is monotonic: each new entity gets a strictly increasing ID.
    - For Sim4 v1, we do NOT reuse IDs once destroyed (ID reuse policy may be revisited later).
    - Tracks which IDs are currently 'alive' for basic validity checks.

    Notes:
    - No randomness or clock access; behavior is deterministic.
    - Instance-scoped allocator; no globals/singletons.
    """

    _next_id: EntityID = 1
    _alive: Set[EntityID] = field(default_factory=set)

    def allocate(self) -> EntityID:
        """
        Allocate and return a new EntityID.

        - Returns the current `_next_id`, marks it as alive,
          then increments `_next_id` for the next call.
        - Must be deterministic: repeated sequences of calls in the
          same order produce the same IDs.
        """
        eid: EntityID = self._next_id
        # Mark alive first, then step next_id for future allocations
        self._alive.add(eid)
        self._next_id = eid + 1
        return eid

    def mark_alive(self, entity_id: EntityID) -> None:
        """
        Mark an externally created entity ID as alive.

        This is mainly for testing or potential future bootstrap paths.
        No-op if already alive.
        """
        if entity_id is None:
            # Defensive no-op; keep behavior deterministic without raising.
            return
        # Only allow positive integers as per spec of small positive IDs.
        if isinstance(entity_id, int) and entity_id >= 1:
            self._alive.add(entity_id)
            # Ensure monotonic invariant: _next_id must always be greater than any allocated/marked id
            if entity_id >= self._next_id:
                self._next_id = entity_id + 1

    def destroy(self, entity_id: EntityID) -> None:
        """
        Mark the given entity ID as no longer alive.

        - If the ID is not alive, this should be a deterministic no-op.
        - Does NOT reuse or roll back `_next_id`.
        """
        # discard() is a deterministic no-op if the element is missing
        self._alive.discard(entity_id)

    def is_alive(self, entity_id: EntityID) -> bool:
        """Return True if the given entity ID is currently marked alive."""
        return entity_id in self._alive

    def alive_ids(self) -> Iterable[EntityID]:
        """
        Return a deterministic iterable of all currently alive IDs,
        sorted in ascending order.
        """
        # Create a new list to avoid exposing internal set; sort for determinism
        ids: List[EntityID] = list(self._alive)
        ids.sort()
        return ids

    def reset(self) -> None:
        """
        Reset allocator to a pristine state (no alive entities, next_id = 1).

        Intended only for tests or controlled scenarios. Not for general runtime use,
        since resetting in-place could violate determinism contracts at higher layers
        if used unexpectedly.
        """
        self._alive.clear()
        self._next_id = 1
