# query.py
from typing import Tuple, Iterator
from .archetype import signature_of

class QueryResult:
    """
    Iterable that yields:
        (EntityID, (compA, compB, compC...))
    using SOA data from ArchetypeStorage.
    """

    def __init__(self, world, comp_types):
        self.world = world
        self.comp_types = comp_types

        # Build the query signature once
        self.signature = signature_of(comp_types)

    def __iter__(self) -> Iterator[Tuple[int, Tuple]]:
        """
        Iterate matching archetypes and yield entity + components.
        """
        # Look through every archetype in the world
        for arch in self.world.archetypes.values():

            # Archetype must contain ALL requested component types
            if not arch.has_components(self.comp_types):
                continue

            # Grab column references (SOA)
            cols = [arch.components[ctype] for ctype in self.comp_types]

            # Iterate row by row
            for row_index, ent_id in enumerate(arch.entities):
                # Extract each component instance
                comps = tuple(col[row_index] for col in cols)
                yield ent_id, comps


class Query:
    """
    Entry point: world.query(Transform, Perception)
    """
    def __init__(self, world, comp_types):
        self.world = world
        self.comp_types = comp_types

    def __iter__(self):
        return iter(QueryResult(self.world, self.comp_types))
