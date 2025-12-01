from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Type

from .entity import EntityAllocator, EntityID
from .archetype import ArchetypeRegistry, ArchetypeSignature
from .storage import ArchetypeStorage


@dataclass
class ECSWorld:
    """
    Minimal ECSWorld skeleton wiring allocator + archetype registry + SOA storages.

    Determinism and Rust-portability:
    - Uses only ints, tuples, lists, and dicts.
    - No randomness or time usage.
    - Per-instance component type code mapping for Python types → small ints.

    Notes on component type codes:
    - For S1.4 we introduce an internal, instance-scoped mapping from Python
      component class objects to small integer "type codes". Codes are assigned
      in first-use order (starting at 1) and are deterministic for a fixed
      sequence of operations. A centralized registry may replace this later.
    """

    allocator: EntityAllocator = field(default_factory=EntityAllocator)
    registry: ArchetypeRegistry = field(default_factory=ArchetypeRegistry)

    # Signature → storage (SOA) for that archetype
    _storages: Dict[ArchetypeSignature, ArchetypeStorage] = field(default_factory=dict)
    # EntityID → (signature, row_index)
    _entities: Dict[EntityID, Tuple[ArchetypeSignature, int]] = field(default_factory=dict)

    # Component type ↔ code mapping (instance-scoped)
    _type_to_code: Dict[Type[object], int] = field(default_factory=dict)
    _code_to_type: Dict[int, Type[object]] = field(default_factory=dict)
    _next_type_code: int = 1

    def __init__(
        self,
        allocator: EntityAllocator | None = None,
        registry: ArchetypeRegistry | None = None,
    ) -> None:
        self.allocator = allocator if allocator is not None else EntityAllocator()
        self.registry = registry if registry is not None else ArchetypeRegistry()
        self._storages = {}
        self._entities = {}
        self._type_to_code = {}
        self._code_to_type = {}
        self._next_type_code = 1

    # ---- Internal helpers ----
    def _get_type_code(self, t: Type[object]) -> int:
        """Return (and if needed assign) a small integer code for a component type."""
        code = self._type_to_code.get(t)
        if code is not None:
            return code
        code = self._next_type_code
        self._next_type_code = code + 1
        self._type_to_code[t] = code
        self._code_to_type[code] = t
        return code

    def _signature_from_types(self, types: Iterable[Type[object]]) -> ArchetypeSignature:
        codes = [self._get_type_code(t) for t in types]
        return ArchetypeSignature.from_type_codes(codes)

    def _ensure_storage(self, signature: ArchetypeSignature) -> ArchetypeStorage:
        st = self._storages.get(signature)
        if st is not None:
            return st
        # Register in archetype registry to obtain a deterministic ID (not used directly now)
        self.registry.get_or_register(signature)
        st = ArchetypeStorage(signature, signature.component_type_codes)
        self._storages[signature] = st
        return st

    def _get_entity_location(
        self, entity_id: EntityID
    ) -> Optional[Tuple[ArchetypeSignature, ArchetypeStorage, int]]:
        loc = self._entities.get(entity_id)
        if loc is None:
            return None
        sig, row = loc
        st = self._storages[sig]
        return sig, st, row

    # ---- Public API ----
    # Entity lifecycle
    def create_entity(self, initial_components: List[object] | None = None) -> EntityID:
        eid = self.allocator.allocate()
        comps = initial_components or []
        comp_types = [type(c) for c in comps]
        signature = self._signature_from_types(comp_types)
        storage = self._ensure_storage(signature)
        # Build initial mapping type_code -> instance
        init_map: Dict[int, object] = {}
        for c in comps:
            init_map[self._get_type_code(type(c))] = c
        row = storage.add_entity(eid, init_map)
        self._entities[eid] = (signature, row)
        return eid

    def destroy_entity(self, entity_id: EntityID) -> None:
        loc = self._entities.get(entity_id)
        if loc is None:
            return  # deterministic no-op
        sig, row = loc
        st = self._storages[sig]
        # Determine if swap-remove will move another entity
        last_index = len(st.entity_ids) - 1
        swapped_entity: Optional[EntityID] = None
        if row != last_index:
            swapped_entity = st.entity_ids[last_index]
        # Remove and capture (values unused here but could be for events later)
        st.remove_entity(entity_id)
        # Update mapping for swapped entity if any
        if swapped_entity is not None:
            self._entities[swapped_entity] = (sig, row)
        # Remove entity from world index and mark dead
        del self._entities[entity_id]
        self.allocator.destroy(entity_id)

    # Components
    def add_component(self, entity_id: EntityID, component_instance: object) -> None:
        loc = self._get_entity_location(entity_id)
        if loc is None:
            return  # no-op for unknown entity
        old_sig, old_st, old_row = loc
        comp_type = type(component_instance)
        code = self._get_type_code(comp_type)
        # If already has this component type, treat as signature change (idempotent move)
        if code in old_sig.component_type_codes:
            # Just set/overwrite the value in place
            old_st.set_component_for_entity(entity_id, code, component_instance)
            return
        new_sig = old_sig.with_component(code)
        new_st = self._ensure_storage(new_sig)

        # Gather old values then remove entity from old storage (to get swap-remove behavior)
        last_index = len(old_st.entity_ids) - 1
        swapped_entity: Optional[EntityID] = None
        if old_row != last_index:
            swapped_entity = old_st.entity_ids[last_index]

        old_values = old_st.remove_entity(entity_id)
        if swapped_entity is not None:
            self._entities[swapped_entity] = (old_sig, old_row)

        # Build new values map for target storage
        new_values: Dict[int, object] = {tc: old_values.get(tc) for tc in old_sig.component_type_codes}
        new_values[code] = component_instance

        new_row = new_st.add_entity(entity_id, new_values)
        self._entities[entity_id] = (new_sig, new_row)

    def remove_component(self, entity_id: EntityID, component_type: Type[object]) -> None:
        loc = self._get_entity_location(entity_id)
        if loc is None:
            return
        old_sig, old_st, old_row = loc
        code = self._get_type_code(component_type)
        if code not in old_sig.component_type_codes:
            return  # deterministic no-op

        new_sig = old_sig.without_component(code)
        new_st = self._ensure_storage(new_sig)

        last_index = len(old_st.entity_ids) - 1
        swapped_entity: Optional[EntityID] = None
        if old_row != last_index:
            swapped_entity = old_st.entity_ids[last_index]
        old_values = old_st.remove_entity(entity_id)
        if swapped_entity is not None:
            self._entities[swapped_entity] = (old_sig, old_row)

        # Build values excluding the removed component
        new_values: Dict[int, object] = {
            tc: v for tc, v in old_values.items() if tc != code
        }
        new_row = new_st.add_entity(entity_id, new_values)
        self._entities[entity_id] = (new_sig, new_row)

    def get_component(self, entity_id: EntityID, component_type: Type[object]) -> object | None:
        loc = self._get_entity_location(entity_id)
        if loc is None:
            return None
        sig, st, _row = loc
        code = self._get_type_code(component_type)
        if code not in sig.component_type_codes:
            return None
        return st.get_component_for_entity(entity_id, code)

    def has_component(self, entity_id: EntityID, component_type: Type[object]) -> bool:
        loc = self._get_entity_location(entity_id)
        if loc is None:
            return False
        sig, _st, _row = loc
        code = self._get_type_code(component_type)
        return code in sig.component_type_codes

    # Query facade
    def query(self, component_types: Tuple[Type[object], ...]) -> "QueryResult":
        # Local import to avoid circular import at module level
        from .query import QuerySignature, QueryResult

        # Normalize order by component type code
        codes_with_types = [(self._get_type_code(t), t) for t in component_types]
        codes_with_types.sort(key=lambda x: x[0])
        norm_types = tuple(t for _c, t in codes_with_types)
        norm_codes = tuple(c for c, _t in codes_with_types)
        qsig = QuerySignature(component_types=norm_types, component_type_codes=norm_codes)
        return QueryResult(world=self, signature=qsig)
