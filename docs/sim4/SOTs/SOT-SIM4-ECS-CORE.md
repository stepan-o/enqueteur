# 📘 SOT-SIM4-ECS-CORE
_ECSWorld, Storage, Entities, Archetypes & Queries_  
Draft 1.0 — Architect-Level, Rust-Aligned, SOP-100/200/300 Compliant

---

## 0. Scope & Purpose

This SOT defines the **ECS substrate kernel** for Sim4:
* `ecs/world.py` — `ECSWorld`
* `ecs/entity.py` — `EntityID` & allocation
* `ecs/storage.py` — SOA / archetype-like storage backend
* `ecs/archetype.py` — archetype layout rules
* `ecs/query.py` — query engine

It answers:
* What **ECSWorld** is and is not.
* How entities & components are stored and mutated.
* How queries expose deterministic read/write views to systems.
* How ECS enforces **determinism**, **layer purity**, and **Rust portability**.
* What public API the runtime + systems SOTs can rely on.

It does **not** define:
* Component schemas → covered by **SOT-ECS-SUBSTRATE-COMPONENTS**.
* System responsibilities → covered by **SOT-ECS-SYSTEMS**.
* Tick phases / runtime scheduling → covered by **SOT-SIM4-RUNTIME-TICK**.

This SOT is the **single source of truth** for the Sim4 ECS substrate core.

---

## 1. Position in the 6-Layer DAG

Per SOP-100, the engine DAG is:
```text
Kernel:   runtime → ecs → world
                \         \
                 \         → snapshot → integration
                  \
                   → (read-only views) → narrative
narrative → (suggestion queues) → runtime (Phase A integration ONLY)
```

Within this DAG:
* `ecs/` is a self-contained, pure **state + query + command-application** layer**.
* `ecs/` **never imports:**
  * `runtime/`
  * `world/`
  * `narrative/`
  * `snapshot/`
  * `integration/`
* All cross-layer interaction flows through:
  * **SystemContext** (defined in SOT-ECS-SYSTEMS) and
  * APIs provided by `ECSWorld` + query engine.

ECS is the **deterministic numeric substrate** on which:
* the agent mind (L1–L5/L7) lives as components, and
* the simulation kernel executes via systems.

---

## 2. Folder Layout (ECS Core)
Canonical structure:
```text
ecs/
    world.py        # ECSWorld — entity registry + storage orchestration
    entity.py       # EntityID type, allocation, tagging helpers
    storage.py      # SOA / archetype storage backend
    archetype.py    # Archetype IDs, layout rules, signatures
    query.py        # Query engine: read/write views over ECSWorld storage
    components/     # (covered by SOT-ECS-SUBSTRATE-COMPONENTS)
    systems/        # (covered by SOT-ECS-SYSTEMS)
```

ECS core types live in these modules only.  
Systems import from `ecs.world`, `ecs.query` and `ecs.components.*` — nothing else.

---

## 3. Entity Model (`ecs/entity.py`)

---

### 3.1 EntityID
* **Type:** opaque, Rust-portable value (e.g. `int` or `NewType[int]`).
* **Requirements:**
  * Unique within a single `ECSWorld` lifespan.
  * Stable across ticks (no reuse until explicit destroy).
  * Comparable & sortable (deterministic ordering).

Conceptual shape:
```text
EntityID = int  # or a small wrapper
```
---

### 3.2 Allocation
`ecs/entity.py` defines an **EntityAllocator** that:
* Hands out new `EntityIDs` in deterministic, monotonically-increasing order.
* Recycles IDs only after explicit destruction:
  * Option 1 (simple Sim4): never recycle within an episode.
  * Option 2 (SimX-ready): use a free-list, but with deterministic strategy.

**Constraints:**

* No random or hash-based ID generation.
* Allocation is purely numeric and trivially portable to Rust.

In the Python Sim4 implementation, `EntityAllocator` additionally tracks a set of “alive” `EntityID`s (`is_alive`, `alive_ids`) and exposes a `reset()` helper and `mark_alive()` for tests/bootstraps. These are implementation conveniences and do not affect the core SOT guarantees (monotonic allocation, no reuse within an episode).

---

### 3.3 Tags & Utility
Optionally:
* Tag helpers (e.g., `ArchetypeCode` enums) live here or in `meta` components.
* They must be **simple ints or enums**, never references to other layers.

---

## 4. ECSWorld (`ecs/world.py`)
### 4.1 Role
`ECSWorld` is:
* The only owner of ECS component data.
* Responsible for:
    * Entity lifecycle (create/destroy).
    * Component attachment/removal.
    * Delegating storage to `storage.py`.
    * Providing query APIs via `query.py`.
    * Applying mutation commands in a deterministic way.

* `ECSWorld` does **not**:
    * Run systems.
    * Know about tick phases.
    * Know about world/narrative/snapshot/integration.

### 4.2 Public API (Conceptual)

High-level methods (shape, not exact signatures):
```python
class ECSWorld:
    # Entity lifecycle
    def create_entity(self, initial_components: list[object] | None = None) -> EntityID: ...
    def destroy_entity(self, entity: EntityID) -> None: ...

    # Component management
    def add_component(self, entity: EntityID, component) -> None: ...
    def remove_component(self, entity: EntityID, component_type: type) -> None: ...
    def get_component(self, entity: EntityID, component_type: type) -> component | None: ...
    def has_component(self, entity: EntityID, component_type: type) -> bool: ...

    # Query API (delegating to query engine)
    def query(self, signature: "QuerySignature") -> "QueryResult": ...

    # Command application (Phase E)
    def apply_commands(self, commands: "Iterable[ECSCommand]") -> None: ...
```

Notes:
* The runtime tick uses `apply_commands()` only in **Phase E**.
* Systems receive `ECSWorld` through a `SystemContext`, but must not call mutating methods directly (they use a command buffer).

### 4.3 Invariants
* For any `EntityID`:
  * either it is **alive** (`ECSWorld.has_entity(id) == True`),
  * or fully destroyed (no components, no storage references).
* No “ghost entities”.
* All component instances for a given entity live in exactly one archetype storage slot.

---

## 5. Storage Model (`ecs/storage.py`)
### 5.1 Design: SOA / Archetype-Oriented
Storage is:
* Columnar (Struct-of-Arrays) per archetype.
* Archetype = **set of component types**.

Each archetype storage holds:
* A dense list of entities belonging to that archetype.
* One dense array per component type.

Conceptual:
```python
@dataclass
class ArchetypeStorage:
    archetype_id: int
    signature: "ArchetypeSignature"  # frozen set/tuple of component types
    entities: list[EntityID]
    columns: dict[type, list[component_instance]]
```

### 5.2 Archetype Management
`storage.py` is responsible for:
* Creating new archetype storages when needed.
* Moving entities between archetypes when components are added/removed.
* Keeping interaction **O(1)** or amortized **O(1)** where possible.

When a component set changes:
1. Determine the new archetype signature.
2. Look up or create the new `ArchetypeStorage`.
3. Move entity & its component values from old → new storage.
4. Maintain **stable ordering** invariants.

### 5.3 Deterministic Ordering
Within `ArchetypeStorage`:
* entities are stored in a list — iteration over entities is in index order.
* Systems must rely on **sorted entity views** (e.g., by `EntityID`) when necessary, not on insertion history, unless explicitly defined.

Global determinism:
* Archetype IDs and their internal order must be **stable** given the same creation sequence.
* No reliance on Python dict/set iteration order.

ArchetypeStorage may use swap-remove internally, so row ordering can change as entities are removed. The invariant is that, for a given sequence of operations, final row order is deterministic. Systems that need ordered views should rely on the query engine’s defined ordering (e.g., ascending `EntityID`), not on raw storage insertion order.

### 5.4 Rust Portability
Storage structures must be mappable to:
* `Vec<EntityId>`
* `Vec<Component>` for each component type.
* `Vec<ArchetypeStorage>` as an array of archetypes.

No:
* Python-only tricks (monkey-patching, dynamic attributes).
* Hidden references to Python objects outside components and IDs.

---

## 6. Archetypes (`ecs/archetype.py`)
### 6.1 ArchetypeSignature
Defines the set of component types for an entity.
* Represented as an ordered tuple of component types or integer IDs.
* Must be hashable & comparable.

Conceptual:
```python
@dataclass(frozen=True)
class ArchetypeSignature:
    component_types: tuple[type, ...]
```

Archetype **ID** is a deterministic mapping from `ArchetypeSignature` → `int`.

---

### 6.2 Signature Rules
* Component type sets are **canonicalized**:
  * Sort by deterministic key (e.g., module + name) before building signature.
* Adding/removing a component always results in moving entity to a **new archetype**.

In the Python implementation, component “type codes” may be assigned per `ECSWorld` instance on first-use, as long as:
* the assignment is deterministic for a given sequence of operations, and
* signatures normalize by sorted type codes.

A static module+name mapping is recommended for Rust, but not required for the Python prototype.

---

### 6.3 Archetype Registry

`archetype.py` maintains a registry:

```python
class ArchetypeRegistry:
    def get_or_register(signature: ArchetypeSignature) -> int: ...
    def get_signature(archetype_id: int) -> ArchetypeSignature: ...
    def ensure_signature(type_codes: Iterable[int]) -> int: ...
```

* The registry maps `ArchetypeSignature ↔ small int archetype_id`.
* It does not own storage. Creation and management of `ArchetypeStorage` instances are handled by `ECSWorld` / `storage.py`, which use the registry to obtain stable archetype IDs.
* This shape is intentionally Rust-portable (mirrors an enum or index into a `Vec<ArchetypeSignature>`).

---

## 7. Query Engine (`ecs/query.py`)
### 7.1 QuerySignature
Defines which components a system is interested in:
* **Read-only** components.
* **Read-write** components.
* Optional **filters** (e.g. “must have component X”, “must not have Y”).

Conceptual:
```python
@dataclass(frozen=True)
class QuerySignature:
    read: tuple[type, ...]
    write: tuple[type, ...]
    optional: tuple[type, ...] = ()
    without: tuple[type, ...] = ()
```

---

### 7.2 QueryResult & RowView layout (Sim4 Python prototype)
The query engine returns a **deterministic iterable** of row views.

RowView.components layout is canonical and fixed-length:

```python
@dataclass(frozen=True)
class RowView:
    entity: EntityID
    # Tuple length = len(read) + len(write) + len(optional)
    # Order is: (read components...) + (write components...) + (optional components...)
    # For optional components that are absent on an entity, the corresponding slot is None.
    components: tuple[object, ...]

class QueryResult:
    def __iter__(self) -> Iterable[RowView]: ...
    def __len__(self) -> int: ...
```

Determinism requirements:
* Iteration order is deterministic. In the Sim4 Python prototype, results are ordered by ascending EntityID. A Rust/SimX implementation may realize this via stable sorting after archetype iteration.
* All entities matching the signature appear exactly once.

---

### 7.3 Read vs Write Semantics
Two conceptual patterns are allowed:
1. **Strict copy semantics inside systems** (preferred for clarity in docs):
* RowView exposes immutable component snapshots.
* System logic uses these snapshots + writes to command buffer.
* Actual component mutation happens in `ECSWorld.apply_commands`.
2. **Borrow-like semantics with guard** (closer to Rust ECS):
* RowView exposes references for reading.
* Write-intent is tracked via `QuerySignature.write`, but mutation still happens via commands.

In all cases, the **SOT contract** is:
* Systems do **not** mutate component attributes directly, even if Python references allow it.
* All writes go through the **command buffer** API.

---

### 7.4 Query Semantics & Implementation
Semantics (Sim4 Sprint 4.5c):
* read + write: the entity must have all of these component types.
* without: the entity must have none of these component types; archetypes/entities possessing any are excluded.
* optional: the entity may or may not have these component types; RowView.components always reserves a slot for each optional type, using None when absent.

Implementation sketch:
* Resolve `QuerySignature` to candidate archetypes using read + write and without filters.
* Iterate deterministically and collect component instances into the RowView.components tuple in the canonical order described above.
* No dynamic introspection or reflection-based queries.

---

## 8. Command Application & Mutation Semantics
While the **command buffer** API is detailed in SOT-ECS-SYSTEMS, the **core behavior** lives here.

### 8.1 ECSCommand (Sprint 4 wrap‑up schema)
Canonical shape aligned with Sim4 implementation and SimX/Rust readiness:
```python
from enum import Enum
from dataclasses import dataclass

class ECSCommandKind(str, Enum):
    SET_FIELD = "set_field"
    SET_COMPONENT = "set_component"
    ADD_COMPONENT = "add_component"
    REMOVE_COMPONENT = "remove_component"
    CREATE_ENTITY = "create_entity"
    DESTROY_ENTITY = "destroy_entity"


@dataclass(frozen=True)
class ECSCommand:
    seq: int
    kind: ECSCommandKind

    # Entity target
    entity_id: int | None = None  # EntityID in code

    # Component targeting
    component_type: type | None = None
    component_type_code: int | None = None  # reserved for SimX/Rust

    # Component payloads
    component_instance: object | None = None
    field_name: str | None = None
    value: object | None = None  # replaces field_value

    # Entity creation / archetype hints
    archetype_code: int | None = None  # reserved for SimX/Rust
    initial_components: list[object] | None = None  # canonical list payload for CREATE_ENTITY
```

Per‑kind field usage (Python prototype):
* SET_COMPONENT: entity_id, component_instance
* SET_FIELD: entity_id, component_type, field_name, value
* ADD_COMPONENT: entity_id, component_instance
* REMOVE_COMPONENT: entity_id, component_type
* CREATE_ENTITY: initial_components (None | list[object])
* DESTROY_ENTITY: entity_id

Implementation status (Sim4 Sprint 4):
* `component_type_code` and `archetype_code` are present on ECSCommand but unused in the Python prototype; they are reserved for SimX/Rust where numeric codes will be canonical.
* In the Python prototype, `CREATE_ENTITY` uses `initial_components` as the canonical payload and `SET_FIELD` uses `value` for the new field value.

### 8.2 `ECSWorld.apply_commands(commands)`
Responsibilities:
* Sorts all commands by `seq` before applying them to guarantee deterministic order.
* Applies the following kinds with these semantics (as implemented):
  * SET_COMPONENT — requires `entity_id` and `component_instance`.
    * Fail‑fast if the entity does not exist.
    * If component type already present, replace; otherwise add (may move archetype).
  * SET_FIELD — requires `entity_id`, `component_type`, `field_name`.
    * Fail‑fast if entity or component is missing, or field does not exist.
    * Performs a Python‑level `setattr` on the component instance (Rust equivalent: struct field write).
  * CREATE_ENTITY — ignores `entity_id` (allocator decides).
    * Expects `component_instance` to be `None` or `list[object]`; attaches listed components deterministically.
    * Raises a deterministic error if payload is not `None | list`.
  * DESTROY_ENTITY — requires `entity_id`.
    * Deterministic no‑op if entity is already gone.
  * ADD_COMPONENT — requires `entity_id` and `component_instance`.
    * Fail‑fast if entity does not exist.
    * Upsert semantics: replace if present, else add (archetype move as needed).
  * REMOVE_COMPONENT — requires `entity_id` and `component_type`.
    * Fail‑fast if entity does not exist.
    * Deterministic no‑op if the entity lacks that component.

Constraints:
* `apply_commands()` is the only place where ECS state is mutated during the tick.
* It must not call systems, narrative, or world.
* Uses only primitives (ints, tuples, lists, dicts, dataclasses) for Rust‑portability.

Mutation rule (runtime): In the production tick pipeline, all ECS mutations originate from commands and are applied via `ECSWorld.apply_commands()` in Phase E. Direct methods like `create_entity`, `destroy_entity`, `add_component`, `remove_component` are available for initialization, scenario loading, and tests, but not for production tick logic.

Implementation note (archetype inference): In Sim4, `ECSWorld.create_entity(initial_components=...)` and `ECSWorld.add_component(...)` infer archetype signatures from the set of component types; no `archetype_code` is exposed to systems.

---

## 9. Determinism & Rust Portability (ECS Core)
### 9.1 Determinism
ECS core must:
* Produce **identical component states** for a given sequence of:
  * initial state
  * commands
  * RNG outcomes (from runtime).
* Never rely on:
  * Python’s hash randomization.
  * Non-deterministic iteration over dict/set.
  * Time-based operations.

Concrete rules:
* Archetype signatures are sorted deterministically.
* Archetype IDs and internal storage indices are reproducible.
* Query iteration order is explicitly defined.

### 9.2 Rust Portability
All ECS core types must:
* Map cleanly to Rust equivalents:
  * `ECSWorld` ↔ struct with `Vec<ArchetypeStorage>`, registries.
  * `ArchetypeStorage` ↔ struct of `Vec<EntityId>` + column `Vec`s.
* Avoid:
  * dynamic attribute magic
  * runtime type mutation
  * deep Python-only inheritance webs.

We treat Python ECS core as a **direct prototype** for a Rust ECS.

---

## 10. Extension Rules
To extend ECS core (Sim5+):
* You may:
  * Add specialized query helpers (e.g. query_one, query_pairs).
  * Add archetype utilities (e.g. debug views, introspection).
* You must not:
  * Introduce cross-layer imports.
  * Hide simulation logic here (logic belongs in systems).
  * Add nondeterministic behavior.

Any substantial change requires:
1. Updating this SOT.
2. Documenting impact on:
  * SOT-ECS-SYSTEMS
  * SOT-SIM4-RUNTIME-TICK
  * Rust migration assumptions.

---

## 11. Completion Condition for SOT-SIM4-ECS-CORE
This SOT is considered **implemented and enforced** when:
1. `ecs/world.py` exposes an `ECSWorld` with:
  * entity lifecycle methods,
  * component management,
  * `query()` access,
  * `apply_commands()` for deterministic mutation.
2. `ecs/entity.py` defines a stable EntityID and allocator with deterministic behavior.
3. `ecs/storage.py` implements:
  * SOA / archetype storage,
  * deterministic entity movement between archetypes.
4. `ecs/archetype.py`:
  * defines ArchetypeSignature,
  * manages archetype IDs & registry deterministically.
5. `ecs/query.py`:
  * defines QuerySignature & QueryResult,
  * returns deterministic entity rows.
6. All ECS state changes originate from:
  * commands built by systems,
  * applied via `ECSWorld.apply_commands()` only in **Phase E** (per SOT-SIM4-RUNTIME-TICK).
7. No ECS core module imports:
  * runtime, world, narrative, snapshot, or integration.

At that point, the ECS core is:
* **Sim4-correct** (for current agent substrate & systems),
* **SimX-ready** (Rust-portable, scalable),
* and fully aligned with the locked core quartet (SOP-000/100/200/300) plus the Sim4 Engine Spec.