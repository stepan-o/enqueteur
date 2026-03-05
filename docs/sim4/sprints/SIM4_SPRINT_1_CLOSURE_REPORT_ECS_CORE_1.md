Sprint 1 – ECS Core Substrate (Closure Report)

Sprint goal
Implement the minimal ECS substrate core for Sim4 (entities, archetypes, storage, and basic querying) in small, testable steps, aligned with SOT-SIM4-ECS-CORE and Rust-portable constraints.

1. Scope Covered
   S1.1 — Entity ID & Allocator ✅

Files:

ecs/entity.py

tests/test_ecs_entity.py

Delivered:

EntityID = int — opaque, Rust-portable integer ID.

EntityAllocator:

Monotonic, deterministic ID allocation starting at 1.

No ID reuse in v1 (destroy does not recycle).

Alive tracking (is_alive, alive_ids).

Test-only helpers: mark_alive, reset.

Notes:

Fully aligned with SOT: deterministic, numeric, Rust-portable.

Alive tracking and helpers are implementation conveniences, not spec changes.

S1.2 — Archetype Signatures & Registry ✅

Files:

ecs/archetype.py

tests/test_ecs_archetype.py

Delivered:

ArchetypeSignature:

Stores component set as tuple[int, ...] of type codes.

Normalization via from_type_codes(...): de-duplicates and sorts ascending.

Helper methods: with_component, without_component (return new signatures).

ArchetypeRegistry:

Deterministic mapping ArchetypeSignature ↔ archetype_id:int.

get_or_register(signature) assigns IDs in insertion order (0-based).

get_signature(archetype_id) with explicit bounds check.

ensure_signature(type_codes) convenience for type-code lists.

Notes:

SOT needs a small textual update:

Registry manages IDs only, not storage; storage is owned by ECSWorld/storage.py.

This is simpler and more Rust-aligned (registry ↔ Vec<ArchetypeSignature>).

S1.3 — Archetype Storage (SOA) Backbone ✅

Files:

ecs/storage.py

tests/test_ecs_storage.py

Delivered:

ArchetypeStorage (SOA layout):

entity_ids: list[EntityID]

entity_index: dict[EntityID, row_index]

columns: dict[type_code:int, list[Any]]

component_type_codes: list[int] (sorted, unique).

Operations:

add_entity(entity_id, initial_components): appends row, fills missing columns with None.

remove_entity(entity_id): swap-remove; returns {type_code -> value} for removed row.

Access helpers: has_entity, get_row_index, get_component_for_entity, set_component_for_entity.

iter_rows() yields (entity_id, {type_code: value, ...}) in index order.

Internal invariant checks:

_assert_lengths() ensures all columns match entity_ids length.

Notes on determinism & ordering:

For a given sequence of add/remove operations, final layout is deterministic.

Swap-remove changes row ordering, but this is acceptable per SOT as long as:

Determinism holds, and

Systems rely on query-defined ordering (not raw storage order).

Recommended SOT clarification: “stable ordering” means deterministic, not “no swap-remove.”

S1.4 — ECSWorld Skeleton & Basic Queries ✅

Files:

ecs/world.py

ecs/query.py

tests/test_ecs_world.py

tests/test_ecs_query.py

Delivered:

ECSWorld (ecs/world.py)

Core fields:

allocator: EntityAllocator

registry: ArchetypeRegistry

_storages: dict[ArchetypeSignature, ArchetypeStorage]

_entities: dict[EntityID, (ArchetypeSignature, row_index)]

Per-world type code maps:

_type_to_code: dict[type, int>

_code_to_type: dict[int, type]

_next_type_code: int

Internal helpers:

_get_type_code(type) -> int: assign small int codes on first use (instance-scoped, deterministic).

_signature_from_types(types) → ArchetypeSignature via codes.

_ensure_storage(signature) → create ArchetypeStorage + register in ArchetypeRegistry.

_get_entity_location(entity_id) → (signature, storage, row_index) | None.

Public API:

create_entity(initial_components: list[object] | None = None) -> EntityID

Infers archetype from type(component_instance) list.

Uses allocator; wires entity into appropriate storage.

destroy_entity(entity_id)

Removes from storage with swap-remove and fixes _entities mapping for swapped entity.

Marks entity as dead in EntityAllocator.

Component operations:

add_component(entity_id, component_instance)

Signature change via with_component(...), old storage → new storage move.

remove_component(entity_id, component_type)

Signature change via without_component(...), with storage move.

get_component(entity_id, component_type) -> object | None

has_component(entity_id, component_type) -> bool

Query facade:

query(component_types: tuple[type, ...]) -> QueryResult

Normalizes component types by ascending type code.

Not yet implemented (intentionally deferred to Sprint 2):

apply_commands(self, commands: Iterable[ECSCommand])

ECSCommand type and command buffer integration.

Query Engine (ecs/query.py)

QuerySignature:

Minimal v1:

@dataclass(frozen=True)
class QuerySignature:
component_types: tuple[type, ...]
component_type_codes: tuple[int, ...]


QueryResult:

Iterable yielding (EntityID, (components...)).

Ordering: ascending EntityID across entire world, independent of archetype.

Implementation:

Takes snapshot of world._entities.keys(), sorts, filters by world.has_component(...), then collects world.get_component(...) in canonical order.

Notes:

Query ordering is fully deterministic and simple to reason about.

Shape is slightly simpler than SOT’s RowView, but semantically equivalent for systems.

Read/write/optional/without axes for queries are left for a future refinement; current engine treats requested components as required-read.

2. Test & Quality Status

All tests for Sprint 1 modules are green:

tests/test_ecs_entity.py — allocation, alive/dead semantics, deterministic sequences.

tests/test_ecs_archetype.py — signature normalization, with/without behavior, registry determinism.

tests/test_ecs_storage.py — add/remove, swap-remove correctness, column alignment, iter_rows.

tests/test_ecs_world.py — entity creation/destruction, component add/remove, invariants between _entities and storages.

tests/test_ecs_query.py — deterministic iteration, correct filtering, component bundles in correct order.

No flakiness observed; CI-ready.

3. Alignment with SOTs & Explicit Deviations
   Fully aligned

Entity model (IDs + allocator): matches SOT-SIM4-ECS-CORE section 3.

SOA storage: matches section 5 (SOA, archetype-based).

Archetype signatures & registry: canonicalized sets, deterministic IDs, Rust-portable representation.

Determinism & portability:

No reliance on dict/set iteration order for visible APIs.

All structures map cleanly to Rust Vec-based ECS.

Deviations / Refinements (to be codified in SOT text)

ArchetypeRegistry responsibilities

SOT originally suggested get_or_create(...) → ArchetypeStorage.

Actual design: registry only maps ArchetypeSignature ↔ int, and storage is managed by ECSWorld.

Action: Update SOT 6.3 to describe ID-only registry; move “storage ownership” explicitly to ECSWorld/storage.

create_entity signature

SOT conceptual: create_entity(archetype_code: int).

Implementation: create_entity(initial_components: list[object] | None).

Interpretation: archetype_code remains a command-level concept; ECSWorld’s public API works via components. SOT should document this Python-specific variant.

Query model

SOT: QuerySignature(read, write, optional, without) and RowView.

Implementation: minimal QuerySignature(component_types, component_type_codes) and QueryResult yielding (EntityID, (components...)).

Action: Note in SOT that Python Sim4 v1 uses a collapsed signature and tuple-based row views, with the richer structure reserved for a later iteration.

Storage ordering vs “stable” wording

Implementation uses swap-remove, so internal row ordering can change.

Still deterministic for a fixed sequence, and systems get sorted EntityID via queries.

Action: Clarify in SOT that “stable ordering” = deterministic, and that systems must rely on query-defined ordering, not raw storage order.

4. Known Gaps (Intentionally Deferred to Later Sprints)

These are not failures of Sprint 1, but planned future work:

ECSCommand definition and semantics (SOT-SIM4-ECS-COMMANDS-AND-EVENTS).

ECSWorld.apply_commands(...) as the only mutation entry point.

ECSCommandBuffer in ecs/systems/base.py and hook-up to tick pipeline.

Richer QuerySignature (read/write/optional/without) and any optimization of query scanning.

Diagnostics / debug helpers for ECSWorld (introspection, counts, basic stats).

5. Risks & Considerations

Per-world type-code mapping:

Type codes are assigned per ECSWorld instance on first use.

Deterministic for a given sequence of operations, and safe for Sim4.

For Rust / multi-process scenarios, we may later move to a static mapping (e.g. module+name → code). SOT will need to explicitly allow both patterns.

Query performance (O(#entities) scan):

Current QueryResult scans all entities and filters via has_component.

For Sim4 scale, this is acceptable; for larger SimX, we may add archetype-based query acceleration later.

The present design keeps the semantics simple for systems and is an intentional trade-off for v1.

6. Ready-for–Sprint-2 Checklist

Sprint 1 is considered complete when:

✅ All Sprint 1 tests pass consistently.

✅ ECSWorld supports:

Deterministic entity lifecycle,

Component attach/detach with archetype moves,

Basic queries returning (EntityID, components...) in ascending ID order.

✅ SOT deltas are either:

Recorded as spec updates, or

Documented as Python-specific implementation notes.

Conclusion:
Sprint 1 successfully delivered a deterministic, Rust-portable ECS substrate backbone (entities, archetypes, storage, world, queries) that matches the architectural intent of SOT-SIM4-ECS-CORE with minor spec text adjustments. The engine is now ready for Sprint 2: ECS Commands & Command Buffer, where we will introduce ECSCommand, ECSCommandBuffer, and ECSWorld.apply_commands() to complete the mutation pipeline used by systems and runtime.