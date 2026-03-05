from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from .entity import EntityID
from .archetype import ArchetypeSignature


@dataclass
class ArchetypeStorage:
    """
    SOA storage for entities sharing the same ArchetypeSignature.

    - Each component type code has its own column (list).
    - Rows are aligned by index across all columns.
    - `entity_ids[row_index]` gives the EntityID for that row.
    - `entity_index[entity_id]` maps to row_index.

    Notes on determinism & portability:
    - component_type_codes are stored as a sorted list of ints.
    - columns are dict[int, list[Any]] mapping type code to a column list.
    - Uses only primitive containers; portable to Rust concepts.
    """

    signature: ArchetypeSignature
    component_type_codes: List[int]

    entity_ids: List[EntityID] = field(default_factory=list)
    entity_index: Dict[EntityID, int] = field(default_factory=dict)
    columns: Dict[int, List[Any]] = field(default_factory=dict)  # type_code -> column list

    def __init__(
        self,
        signature: ArchetypeSignature,
        component_type_codes: Iterable[int],
    ) -> None:
        # Normalize and store component codes deterministically
        codes = sorted({int(c) for c in component_type_codes})
        self.signature = signature
        self.component_type_codes = list(codes)
        self.entity_ids = []
        self.entity_index = {}
        # Initialize empty columns for each code
        self.columns = {tc: [] for tc in self.component_type_codes}

    # ---- Core API ----
    def add_entity(
        self,
        entity_id: EntityID,
        initial_components: Mapping[int, Any] | None = None,
    ) -> int:
        """
        Add an entity to this archetype.

        - Appends a new row to `entity_ids` and each column.
        - `initial_components` maps component_type_code -> component instance.
        - Any component codes missing in `initial_components` are filled with None.

        Returns: row_index for the newly added entity.
        Raises: ValueError if the entity_id is already present.
        """
        if entity_id in self.entity_index:
            raise ValueError(f"Entity already present in archetype storage: {entity_id}")

        row_index = len(self.entity_ids)
        self.entity_ids.append(entity_id)
        self.entity_index[entity_id] = row_index

        comp_map: Mapping[int, Any] = initial_components or {}

        # Append per-column values in deterministic component code order
        for tc in self.component_type_codes:
            value = comp_map[tc] if tc in comp_map else None
            self.columns[tc].append(value)

        # Invariant: lengths must match
        self._assert_lengths()
        return row_index

    def remove_entity(self, entity_id: EntityID) -> Dict[int, Any]:
        """
        Remove an entity from this archetype using swap-remove.

        Returns: dict mapping component_type_code -> component instance that
        belonged to the removed entity.
        Raises: KeyError if the entity_id is not present.
        """
        if entity_id not in self.entity_index:
            raise KeyError(entity_id)

        row_index = self.entity_index[entity_id]
        last_index = len(self.entity_ids) - 1
        # Capture removed values before mutation
        removed_values: Dict[int, Any] = {tc: self.columns[tc][row_index] for tc in self.component_type_codes}

        if row_index == last_index:
            # Simply pop last row
            self.entity_ids.pop()
            for tc in self.component_type_codes:
                self.columns[tc].pop()
            del self.entity_index[entity_id]
        else:
            # Swap last row into row_index
            last_entity_id = self.entity_ids[last_index]
            self.entity_ids[row_index] = last_entity_id
            self.entity_ids.pop()  # shrink

            for tc in self.component_type_codes:
                col = self.columns[tc]
                col[row_index] = col[last_index]
                col.pop()

            # Update index for swapped entity
            self.entity_index[last_entity_id] = row_index
            del self.entity_index[entity_id]

        # Invariant: lengths must match
        self._assert_lengths()
        return removed_values

    # ---- Access helpers ----
    def has_entity(self, entity_id: EntityID) -> bool:
        return entity_id in self.entity_index

    def get_row_index(self, entity_id: EntityID) -> int:
        if entity_id not in self.entity_index:
            raise KeyError(entity_id)
        return self.entity_index[entity_id]

    def get_component_for_entity(self, entity_id: EntityID, component_type_code: int) -> Any:
        if component_type_code not in self.columns:
            raise KeyError(component_type_code)
        row = self.get_row_index(entity_id)
        return self.columns[component_type_code][row]

    def set_component_for_entity(self, entity_id: EntityID, component_type_code: int, value: Any) -> None:
        if component_type_code not in self.columns:
            raise KeyError(component_type_code)
        row = self.get_row_index(entity_id)
        self.columns[component_type_code][row] = value

    def iter_rows(self) -> Iterable[Tuple[EntityID, Dict[int, Any]]]:
        """Yield (entity_id, {type_code: value, ...}) for each row in order."""
        # Deterministic row order is entity_ids order
        for i, eid in enumerate(self.entity_ids):
            row_values = {tc: self.columns[tc][i] for tc in self.component_type_codes}
            yield eid, row_values

    # ---- Internal invariants ----
    def _assert_lengths(self) -> None:
        """Assert internal invariant that all columns align with entity_ids length."""
        n = len(self.entity_ids)
        for tc in self.component_type_codes:
            assert len(self.columns[tc]) == n, "Column length mismatch with entity_ids"
