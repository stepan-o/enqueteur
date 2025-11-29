# archetype.py
from typing import Dict, List, Type, Any
from .entity import EntityID


def signature_of(component_types: tuple[Type]):
    """
    Normalize component type list → sorted tuple.
    Ensures stable hash + archetype identity.
    """
    return tuple(sorted(component_types, key=lambda c: c.__name__))


class Archetype:
    """
    An archetype stores entities and their components in SOA form.
    Each Archetype instance corresponds to a unique combination
    of component types.
    """

    def __init__(self, component_types: tuple[Type]):
        self.component_types = component_types      # (Transform, Velocity, ...)
        self.signature = signature_of(component_types)

        # SOA storage: comp_type → list of values
        self.columns: Dict[Type, List[Any]] = {
            c: [] for c in component_types
        }

        # entity list
        self.entities: List[EntityID] = []

        # entity → row index
        self.row_index: Dict[EntityID, int] = {}

    # ------------------------------------------------------------------
    # INSERT ENTITY
    # ------------------------------------------------------------------
    def add_entity(self, ent: EntityID, values: Dict[Type, Any]):
        """
        Add entity to this archetype given a dict:
        {ComponentType: component_instance}
        """
        row = len(self.entities)
        self.entities.append(ent)
        self.row_index[ent] = row

        # append each component in order
        for comp_type in self.component_types:
            self.columns[comp_type].append(values[comp_type])

    # ------------------------------------------------------------------
    # REMOVE ENTITY
    # ------------------------------------------------------------------
    def remove_entity(self, ent: EntityID):
        """
        Remove entity using swap-delete to keep arrays tight.
        """
        row = self.row_index.pop(ent)
        last_row = len(self.entities) - 1

        if row != last_row:
            last_ent = self.entities[last_row]

            # move last entity into removed spot
            self.entities[row] = last_ent
            self.row_index[last_ent] = row

            for ctype in self.component_types:
                col = self.columns[ctype]
                col[row] = col[last_row]

        # remove last element
        self.entities.pop()
        for ctype in self.component_types:
            self.columns[ctype].pop()

    # ------------------------------------------------------------------
    # LOOKUP COMPONENTS
    # ------------------------------------------------------------------
    def get_components(self, ent: EntityID) -> Dict[Type, Any]:
        row = self.row_index[ent]
        return {
            ctype: self.columns[ctype][row]
            for ctype in self.component_types
        }

    # ------------------------------------------------------------------
    # ITERATION
    # ------------------------------------------------------------------
    def iter(self, *ctypes: Type):
        """
        Iterate over rows that contain these component types.
        Return tuples: (ent, [components...])
        """
        for i, ent in enumerate(self.entities):
            comps = [self.columns[ctype][i] for ctype in ctypes]
            yield ent, comps
