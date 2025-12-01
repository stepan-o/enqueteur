from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Type

from .entity import EntityAllocator, EntityID
from .archetype import ArchetypeRegistry, ArchetypeSignature
from .storage import ArchetypeStorage
from .commands import ECSCommand, ECSCommandKind


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

    # Query facade (Sprint 4.5a)
    def query(self, signature: "QuerySignature") -> "QueryResult":
        """
        Execute an ECS query described by a QuerySignature.

        - Only QuerySignature is accepted (no legacy tuple API).
        - Result ordering is deterministic (ascending by EntityID for now),
          which is relied upon by tests and SOT-SIM4-ECS-CORE. Later sprints
          may refine ordering to (archetype_id, entity_id) without breaking
          determinism.
        """
        # Local import to avoid circular imports at module level
        from .query import QuerySignature, QueryResult, RowView

        if not isinstance(signature, QuerySignature):
            raise TypeError("ECSWorld.query expects a QuerySignature")

        # For 4.5a, matching considers read + write sets only.
        # optional/without are threaded structurally but not enforced yet.
        read_types = signature.read
        write_types = signature.write
        opt_types = signature.optional

        all_fetch_types: Tuple[Type[object], ...] = tuple(read_types + write_types + opt_types)  # type: ignore[operator]

        # Deterministic iteration over entity IDs.
        ids = sorted(self._entities.keys())

        rows: list[RowView] = []
        for eid in ids:
            # Must have all read + write component types
            missing = False
            for t in read_types + write_types:  # type: ignore[operator]
                if not self.has_component(eid, t):
                    missing = True
                    break
            if missing:
                continue

            # Gather components in canonical order: read + write + optional
            comps: list[object] = []
            for t in all_fetch_types:
                comp = self.get_component(eid, t)
                comps.append(comp)
            rows.append(RowView(entity=eid, components=tuple(comps)))

        return QueryResult(rows)

    # ---- Existence helper ----
    def has_entity(self, entity_id: EntityID) -> bool:
        """Return True if the entity_id exists in this world."""
        return entity_id in self._entities

    # ---- Command application (S2.2 + S2.3) ----
    def apply_commands(self, commands: Iterable[ECSCommand]) -> None:
        """
        Apply a batch of ECSCommands in a deterministic order.

        Supported kinds after Sub-Sprint 2.3:
        - SET_COMPONENT
        - SET_FIELD
        - CREATE_ENTITY
        - DESTROY_ENTITY
        - ADD_COMPONENT
        - REMOVE_COMPONENT
        """
        # 1) sort by seq for determinism
        sorted_cmds = sorted(commands, key=lambda c: c.seq)

        # 2) dispatch per kind
        for cmd in sorted_cmds:
            if cmd.kind is ECSCommandKind.SET_COMPONENT:
                self._apply_set_component(cmd)
            elif cmd.kind is ECSCommandKind.SET_FIELD:
                self._apply_set_field(cmd)
            elif cmd.kind is ECSCommandKind.CREATE_ENTITY:
                self._apply_create_entity(cmd)
            elif cmd.kind is ECSCommandKind.DESTROY_ENTITY:
                self._apply_destroy_entity(cmd)
            elif cmd.kind is ECSCommandKind.ADD_COMPONENT:
                self._apply_add_component(cmd)
            elif cmd.kind is ECSCommandKind.REMOVE_COMPONENT:
                self._apply_remove_component(cmd)
            else:
                raise NotImplementedError(
                    f"ECSWorld.apply_commands: command kind {cmd.kind} not supported"
                )

    def _apply_set_component(self, cmd: ECSCommand) -> None:
        # Validate required fields
        if cmd.entity_id is None or cmd.component_instance is None:
            raise ValueError(
                "SET_COMPONENT command requires entity_id and component_instance"
            )

        entity_id = cmd.entity_id
        component_instance = cmd.component_instance
        comp_type = type(component_instance)

        # Strict check: entity must exist
        if not self.has_entity(entity_id):
            raise ValueError(f"SET_COMPONENT: entity {entity_id} does not exist")

        # Semantics: if entity already has the type, replace it; otherwise add it.
        # Our add_component already overwrites in-place when component exists.
        self.add_component(entity_id, component_instance)

    def _apply_set_field(self, cmd: ECSCommand) -> None:
        if (
            cmd.entity_id is None
            or cmd.component_type is None
            or cmd.field_name is None
        ):
            raise ValueError(
                "SET_FIELD command requires entity_id, component_type, and field_name"
            )

        entity_id = cmd.entity_id
        component_type = cmd.component_type
        field_name = cmd.field_name
        field_value = cmd.field_value

        # Strict checks for determinism / early bug surfacing
        if not self.has_entity(entity_id):
            raise ValueError(f"SET_FIELD: entity {entity_id} does not exist")

        component = self.get_component(entity_id, component_type)
        if component is None:
            raise ValueError(
                f"SET_FIELD: entity {entity_id} does not have component {component_type}"
            )

        if not hasattr(component, field_name):
            raise AttributeError(
                f"SET_FIELD: component {component_type} has no field '{field_name}'"
            )

        setattr(component, field_name, field_value)

    # ---- New command helpers for S2.3 ----
    def _apply_create_entity(self, cmd: ECSCommand) -> None:
        """
        CREATE_ENTITY semantics for S2.3:
        - Ignore cmd.entity_id (IDs come from allocator).
        - cmd.component_instance is treated as Optional[list[object]] payload.
        - Components (if provided) are attached deterministically.

        Note: Overloading of component_instance as a list payload is an
        interim compromise for Sprint 2.
        """
        payload = cmd.component_instance
        if payload is None:
            components_list: List[object] = []
        else:
            if not isinstance(payload, list):
                raise ValueError(
                    "CREATE_ENTITY expects component_instance to be None or list[object]"
                )
            components_list = payload

        # We could pass to create_entity directly; we keep explicit add for clarity
        eid = self.create_entity()
        for comp in components_list:
            self.add_component(eid, comp)

    def _apply_destroy_entity(self, cmd: ECSCommand) -> None:
        if cmd.entity_id is None:
            raise ValueError("DESTROY_ENTITY command requires entity_id")
        eid = cmd.entity_id
        if not self.has_entity(eid):
            # Deterministic no-op
            return
        self.destroy_entity(eid)

    def _apply_add_component(self, cmd: ECSCommand) -> None:
        if cmd.entity_id is None or cmd.component_instance is None:
            raise ValueError(
                "ADD_COMPONENT command requires entity_id and component_instance"
            )
        eid = cmd.entity_id
        comp = cmd.component_instance
        if not self.has_entity(eid):
            raise ValueError(f"ADD_COMPONENT: entity {eid} does not exist")
        # Upsert semantics: replace if exists, else add
        existing = self.get_component(eid, type(comp))
        if existing is None:
            self.add_component(eid, comp)
        else:
            # reuse same logic as set_component path
            self.add_component(eid, comp)

    def _apply_remove_component(self, cmd: ECSCommand) -> None:
        if cmd.entity_id is None or cmd.component_type is None:
            raise ValueError(
                "REMOVE_COMPONENT command requires entity_id and component_type"
            )
        eid = cmd.entity_id
        ctype = cmd.component_type
        if not self.has_entity(eid):
            raise ValueError(f"REMOVE_COMPONENT: entity {eid} does not exist")
        if not self.has_component(eid, ctype):
            # Deterministic no-op
            return
        self.remove_component(eid, ctype)

    # ---- Small helper for tests/inspection ----
    def iter_entity_ids(self) -> Iterable[EntityID]:
        """Yield EntityIDs in ascending order (deterministic)."""
        ids = list(self._entities.keys())
        ids.sort()
        return iter(ids)
