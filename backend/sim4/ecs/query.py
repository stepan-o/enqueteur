from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Tuple, Type

from .entity import EntityID


@dataclass(frozen=True)
class QuerySignature:
    """
    Normalized query over component types.

    - component_types: canonical order corresponding to component_type_codes order
    - component_type_codes: tuple of int codes, sorted ascending

    ECSWorld.query(...) is responsible for constructing a normalized signature
    using the world's component type code mapping to ensure determinism.
    """

    component_types: Tuple[Type[object], ...]
    component_type_codes: Tuple[int, ...]


@dataclass
class QueryResult:
    """
    Iterable of (EntityID, (components...)) for entities matching a QuerySignature.

    Ordering: ascending EntityID across the whole world, regardless of archetype.
    """

    world: "ECSWorld"
    signature: QuerySignature

    def __iter__(self) -> Iterator[tuple[EntityID, tuple[object, ...]]]:
        # To ensure deterministic global ordering, iterate entity IDs in
        # ascending order and filter by component presence.
        # Import inside to avoid circular at module import time.
        world = self.world
        type_codes = self.signature.component_type_codes
        comp_types = self.signature.component_types

        # Collect and iterate in ascending EntityID order
        ids = list(world._entities.keys())  # pylint: disable=protected-access
        ids.sort()
        for eid in ids:
            # Fast pre-check: ensure entity has all required components
            has_all = True
            for t in comp_types:
                if not world.has_component(eid, t):
                    has_all = False
                    break
            if not has_all:
                continue
            # Fetch in the canonical query order
            comps = tuple(world.get_component(eid, t) for t in comp_types)
            yield eid, comps

    def to_list(self) -> list[tuple[EntityID, tuple[object, ...]]]:
        return list(self.__iter__())
