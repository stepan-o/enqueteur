# storage.py
from typing import Dict, List, Type
from .archetype import signature_of
from ..ecs.entity import EntityID


class ArchetypeStorage:
    """
    Structure-of-Arrays storage for a single archetype signature.

    Features:
    - O(1) add and remove (swap-delete)
    - entity → row reverse lookup
    - SOA columns for each component type
    - fully deterministic iteration
    """

    def __init__(self, comp_types: List[Type]):
        self.comp_types = tuple(comp_types)
        self.signature = signature_of(comp_types)

        # SOA arrays
        self.entities: List[EntityID] = []
        self.components: Dict[Type, List] = {ctype: [] for ctype in comp_types}

        # Reverse lookup: entity → row index
        self.entity_to_row: Dict[EntityID, int] = {}

    # --------------------------------------------------------------
    # ADD
    # --------------------------------------------------------------
    def add_entity(self, ent_id: EntityID, comp_values: Dict[Type, object]):
        row = len(self.entities)

        self.entities.append(ent_id)
        self.entity_to_row[ent_id] = row

        # Append component values in SOA layout
        for ctype in self.comp_types:
            self.components[ctype].append(comp_values.get(ctype))

    # --------------------------------------------------------------
    # REMOVE (swap-delete)
    # --------------------------------------------------------------
    def remove_entity(self, ent_id: EntityID):
        row = self.entity_to_row.pop(ent_id)
        last_row = len(self.entities) - 1

        # If this is the last element → simple pop
        if row == last_row:
            self.entities.pop()
            for col in self.components.values():
                col.pop()
            return

        # Otherwise swap the last row into this row, then pop
        last_ent = self.entities[last_row]

        # Move entity ID
        self.entities[row] = last_ent
        self.entities.pop()

        # Move component values
        for ctype, col in self.components.items():
            col[row] = col[last_row]
            col.pop()

        # Update moved entity's row mapping
        self.entity_to_row[last_ent] = row

    # --------------------------------------------------------------
    # CHECK COMPONENT MEMBERSHIP
    # --------------------------------------------------------------
    def has_components(self, comp_types):
        return all(ctype in self.components for ctype in comp_types)

    # --------------------------------------------------------------
    # GET / SET (fast)
    # --------------------------------------------------------------
    def get_component(self, ent_id: EntityID, ctype):
        row = self.entity_to_row[ent_id]
        return self.components[ctype][row]

    def set_component(self, ent_id: EntityID, ctype, value):
        row = self.entity_to_row[ent_id]
        self.components[ctype][row] = value

    # --------------------------------------------------------------
    # ITERATION HELPERS (optional)
    # --------------------------------------------------------------
    def iter_rows(self):
        """
        Yields row index and EntityID.
        """
        for row, ent in enumerate(self.entities):
            yield row, ent
