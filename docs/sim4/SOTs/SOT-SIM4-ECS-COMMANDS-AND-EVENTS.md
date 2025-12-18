# 📘 SOT-SIM4-ECS-COMMANDS-AND-EVENTS
_**ECSCommand, WorldCommand, WorldEvent**_  
**Draft 1.1 — Architect-Level, Rust-Aligned, SOP-100/200/300 Compliant**

---

## 0. Scope & Purpose
This SOT unifies and locks the Sim4 **command/event vocabulary** used by:
- ECS (substrate + systems)
- World Engine / WorldContext
- Runtime tick, history, snapshot builders, and narrative inputs

It defines:
- Canonical schemas for:
    - `ECSCommand`
    - `WorldCommand`
    - `WorldEvent`
- Allowed kind values for:
    - `ECSCommandKind`
    - `WorldCommandKind`
    - `WorldEventKind`
- Construction + application semantics
- Deterministic ordering + error rules
- Tick-phase integration (SOT-SIM4-RUNTIME-TICK)

This SOT ties together:
- SOT-SIM4-ECS-CORE (ECSWorld + apply_commands)
- SOT-SIM4-ECS-SYSTEMS (who emits what)
- SOT-SIM4-WORLD-ENGINE (WorldContext, command application)
- SOT-SIM4-RUNTIME-TICK (phase sequencing)
- SOT-SIM4-SNAPSHOT-AND-EPISODE (event-based summaries)

**Single source of truth:** command + event types and kind enums.

---

## 1. Position in the 6-Layer DAG
DAG reminder:
```text
Kernel:   runtime → ecs → world
                \         \
                 \         → snapshot → integration
                  \
                   → (read-only views) → narrative
narrative → (suggestion queues) → runtime (Phase A integration ONLY)
```
Where commands/events sit:
- **ECSCommand**: consumed by `ECSWorld.apply_commands()` (Phase E)
- **WorldCommand**: consumed by `WorldContext.apply_world_commands()` (Phase F)
- **WorldEvent**: emitted during world application (Phase F) and consolidation (Phase G)

Runtime owns buffers and sequencing:
- collects ECS + world commands from systems
- applies commands in Phase E then Phase F
- aggregates events in Phase G
- stores events in history and feeds snapshot/narrative contexts

Hard constraints (SOP-100):
- ECS never directly mutates WorldContext
- WorldContext never directly mutates ECSWorld
- Narrative never issues raw ECSCommand/WorldCommand (only substrate suggestions)

SOP-200 determinism requirements apply to:
- ordering (seq)
- stable kinds (string enums)
- payload shapes (primitives-only, Rust-portable)

---

## 2. Folder Layout & Ownership
Canonical locations:
```text
backend/sim4/ecs/
  commands.py        # ECSCommand + ECSCommandKind
  world.py           # ECSWorld.apply_commands(...)

backend/sim4/world/
  commands.py        # WorldCommand + WorldCommandKind
  events.py          # WorldEvent + WorldEventKind
  apply_world_commands.py  # canonical applier (if split from WorldContext)

backend/sim4/runtime/
  tick_loop.py / tick.py   # orchestrates phases
  history.py               # records events and diffs
  command_bus.py           # (optional) buffers + routing + seq assignment
```

Ownership:
- `ecs/commands.py` belongs to ECS layer.
- `world/commands.py` + `world/events.py` belong to world layer.
- Runtime uses these types but does not redefine them.

Layer import rules:
- ECS may import ECS types only; must not import world/runtime.
- World may import world types only; must not import ecs/runtime.
- Runtime may import both ECS and world types.
- Snapshot/integration may read events via history/snapshots only (no direct command use).

---

## 3. ECSCommand
### 3.1 Canonical Schema (Rust-aligned)
ECS commands are the **only** mutation mechanism for ECSWorld.

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

class ECSCommandKind(str, Enum):
    SET_FIELD = "set_field"
    SET_COMPONENT = "set_component"
    ADD_COMPONENT = "add_component"
    REMOVE_COMPONENT = "remove_component"
    CREATE_ENTITY = "create_entity"
    DESTROY_ENTITY = "destroy_entity"

@dataclass(frozen=True)
class ECSCommand:
    seq: int                       # tick-local monotonic sequence (global within tick)
    kind: ECSCommandKind           # stable string enum

    entity_id: int | None = None

    # Component targeting
    component_type: type | None = None            # Python convenience (not Rust-canonical)
    component_type_code: int | None = None        # Rust/SimX canonical type id

    # Payload variants
    component_instance: Any | None = None         # SET_COMPONENT / ADD_COMPONENT
    field_name: str | None = None                 # SET_FIELD
    value: Any | None = None                      # SET_FIELD

    # Entity creation hints
    archetype_code: int | None = None             # reserved for Rust
    initial_components: list[Any] | None = None   # CREATE_ENTITY canonical payload
```

---

### 3.2 Per-kind Field Usage
- `SET_COMPONENT`:
  - requires: `entity_id`, `component_instance`
- `ADD_COMPONENT`:
  - requires: `entity_id`, `component_instance`
- `REMOVE_COMPONENT`:
  - requires: `entity_id`, (`component_type` or `component_type_code`)
- `SET_FIELD`:
  - requires: `entity_id`, (`component_type` or `component_type_code`), `field_name`, `value`
- `CREATE_ENTITY`:
  - uses: `initial_components` (optional), `archetype_code` (optional)
  - `entity_id` MUST be None (allocated by ECSWorld)
- `DESTROY_ENTITY`:
  - requires: `entity_id`

Notes:
- `component_type_code` is the Rust-portable identifier. Python `type` is convenience only.
- Historical fields like `field_value` are removed; use `value`.
- `initial_components` is the canonical CREATE_ENTITY payload (do not overload `component_instance`).

---

### 3.3 Application Semantics (ECSWorld.apply_commands)
`ECSWorld.apply_commands(commands)` must:
- convert iterable → list
- **sort by `seq` ascending** (stable)
- apply each exactly once

Semantics (Python prototype):
- `SET_COMPONENT` / `ADD_COMPONENT`:
  - upsert component instance on entity
  - entity must exist; missing entity → error (fail fast)
- `REMOVE_COMPONENT`:
  - remove if present; missing component → deterministic no-op
- `SET_FIELD`:
  - entity + component must exist; field must exist
  - missing required fields → ValueError; missing attribute → AttributeError
- `CREATE_ENTITY`:
  - allocate new entity id deterministically
  - attach `initial_components` in deterministic order if provided
- `DESTROY_ENTITY`:
  - remove entity and all components; mark id dead (recycling policy per ECS CORE)

Determinism:
- command ordering is by `seq` only (no dict iteration, no randomness).
- errors are deterministic (same input → same exception point).

---

## 4. WorldCommand
World commands express environment-level changes handled by WorldContext
(rooms, doors, occupancy, item registries), not ECS component storage.

### 4.1 Canonical Schema (primitives-only, Rust-portable)
To avoid schema drift, **WorldCommand is a tagged payload** (kind + payload dict),
with optional anchor fields for indexing/search.

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any

class WorldCommandKind(str, Enum):
    # Movement / placement
    SET_AGENT_ROOM = "set_agent_room"
    MOVE_AGENT_PATH = "move_agent_path"

    # Doors / portals
    OPEN_DOOR = "open_door"
    CLOSE_DOOR = "close_door"

    # Items
    SPAWN_ITEM = "spawn_item"
    DESPAWN_ITEM = "despawn_item"
    SET_ITEM_ROOM = "set_item_room"
    SET_ITEM_OWNER = "set_item_owner"

    # Room/world state + tags
    SET_ROOM_STATE = "set_room_state"
    TAG_ROOM = "tag_room"
    TAG_AGENT = "tag_agent"

@dataclass(frozen=True)
class WorldCommand:
    seq: int                 # tick-local monotonic sequence (sorted ascending before apply)
    kind: WorldCommandKind   # stable string enum

    # Optional anchors (for filtering/indexing; do not duplicate payload truth)
    actor_agent_id: int | None = None
    room_id: int | None = None

    payload: dict[str, Any] = None
```

---

### 4.2 Payload Contracts (Recommended Keys)
The payload keys below are the canonical contract by kind.

#### SET_AGENT_ROOM
```json
{ "agent_id": int, "from_room_id": int|null, "to_room_id": int }
```

#### MOVE_AGENT_PATH (optional high-level)
```json
{ "agent_id": int, "room_sequence": [int, ...] }
```

#### OPEN_DOOR / CLOSE_DOOR
```json
{ "door_id": int }
```

#### SPAWN_ITEM
```json
{ "item_id": int|null, "room_id": int|null, "owner_agent_id": int|null, "item_kind_code": int }
```

#### DESPAWN_ITEM
```json
{ "item_id": int }
```

#### SET_ITEM_ROOM
```json
{ "item_id": int, "from_room_id": int|null, "to_room_id": int|null }
```

#### SET_ITEM_OWNER
```json
{ "item_id": int, "from_owner_agent_id": int|null, "to_owner_agent_id": int|null }
```

#### SET_ROOM_STATE
```json
{ "room_id": int, "state_code": int }
```

#### TAG_ROOM / TAG_AGENT
```json
{ "room_id": int, "tag_code": int }
{ "agent_id": int, "tag_code": int }
```
Rule: payloads contain primitives only (ints, floats, bools, strings, arrays, dicts).
No arbitrary Python objects, no handles, no free-text semantics beyond debug labels.

---

### 4.3 World Command Application Semantics
World commands are applied by a canonical applier (e.g. `apply_world_commands.py`)
or `WorldContext.apply_world_commands(commands)` which must:
- convert iterable → list
- **sort by `seq` ascending** (stable)
- apply each command via public WorldContext helpers (no direct dict mutations)
- emit `WorldEvent` instances for **successful mutations only**
- propagate errors for invalid commands
- raise `NotImplementedError` for unknown command kinds

Deterministic guarantees:
- same command list + same world state → same mutations + same emitted events
- no RNG, no wall-clock, no iteration over unordered collections without sorting

Compatibility note:
- Earlier prototypes used “flat optional id fields” (agent_id/room_id/item_id/door_id).
  That approach is deprecated in favor of a single `payload` contract to prevent drift.

---

## 5. WorldEvent
World events are append-only facts produced during world mutation and consolidation.
They feed:
- runtime history
- snapshot/episode builders
- narrative tick contexts (as read-only inputs)

### 5.1 Canonical Schema (primitives-only)
```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any

class WorldEventKind(str, Enum):
    # Movement & presence
    AGENT_MOVED = "agent_moved"
    AGENT_ENTERED_ROOM = "agent_entered_room"
    AGENT_LEFT_ROOM = "agent_left_room"

    # Doors / portals
    DOOR_OPENED = "door_opened"
    DOOR_CLOSED = "door_closed"

    # Items / inventory
    ITEM_SPAWNED = "item_spawned"
    ITEM_DESPAWNED = "item_despawned"
    ITEM_PICKED_UP = "item_picked_up"
    ITEM_DROPPED = "item_dropped"
    ITEM_EQUIPPED = "item_equipped"
    ITEM_UNEQUIPPED = "item_unequipped"

    # Interactions
    INTERACTION_COMPLETED = "interaction_completed"

    # Derived summaries (post-apply)
    RELATIONSHIP_CHANGED = "relationship_changed"
    TENSION_SPIKE = "tension_spike"

    # Debug/meta
    TICK_MARKER = "tick_marker"

@dataclass(frozen=True)
class WorldEvent:
    tick_index: int
    kind: WorldEventKind
    importance: float = 0.0          # numeric hint for downstream consumers

    actor_agent_id: int | None = None
    target_agent_id: int | None = None
    room_id: int | None = None
    item_id: int | None = None
    door_id: int | None = None

    payload: dict[str, Any] = None
```

### 5.2 Recommended Payloads (Canonical Keys)
#### AGENT_MOVED
```json
{ "agent_id": int, "from_room_id": int|null, "to_room_id": int }
```

#### AGENT_ENTERED_ROOM / AGENT_LEFT_ROOM
```json
{ "agent_id": int, "room_id": int }
```

#### DOOR_OPENED / DOOR_CLOSED
```json
{ "door_id": int, "room_a_id": int, "room_b_id": int }
```

#### ITEM_SPAWNED / ITEM_DESPAWNED
```json
{ "item_id": int, "room_id": int|null, "owner_agent_id": int|null, "item_kind_code": int }
```

#### ITEM_PICKED_UP / ITEM_DROPPED / ITEM_EQUIPPED / ITEM_UNEQUIPPED
```json
{ "agent_id": int, "item_id": int,
  "from_room_id": int|null, "to_room_id": int|null,
  "slot_code": int|null }
```

#### INTERACTION_COMPLETED
```json
{ "interaction_kind_code": int, "success": bool,
  "actor_agent_id": int, "target_agent_id": int|null }
```

#### RELATIONSHIP_CHANGED (derived)
```json
{ "agent_a_id": int, "agent_b_id": int,
  "delta": float, "new_value": float }
```

#### TENSION_SPIKE (derived)
```json
{ "room_id": int, "old_tension": float, "new_tension": float }
```

#### TICK_MARKER (debug/meta)
```json
{ "label": "short string" }
```

---

### 5.3 Event Emission Rules
- Events are emitted during:
  - Phase F (world command application) and
  - Phase G (event consolidation / derived summarization)
- Events are append-only; never mutated in place.
- Importance is a downstream hint only:
  - snapshot/episode builders may use it for scene segmentation / highlights
  - narrative may use it as a salience cue
  - substrate must not branch on it

Deterministic ordering:
- If multiple events are emitted in a tick:
  - they must be recorded in a stable order derived from the command `seq`
  - and/or an internal deterministic `event_seq` (if implemented)
- Never rely on unordered container iteration for event output order.

---

## 6. Integration with Tick Phases (Runtime)
Per SOT-SIM4-RUNTIME-TICK:

### Phases B–D (ECS systems)
Systems:
- read ECS state + WorldViews (read-only)
- emit:
  - `ECSCommand` via ECSCommandBuffer
  - `WorldCommand` via world-command buffer
All emitted commands receive monotonic `seq` indices.

### Phase E — ECS Command Application
Runtime calls:
- `ECSWorld.apply_commands(ecs_commands)`
ECSWorld:
- applies CREATE/DESTROY/ADD/REMOVE/SET_COMPONENT/SET_FIELD
- updates archetype storage deterministically

### Phase F — World Command Application
Runtime calls:
- `WorldContext.apply_world_commands(world_commands)`
World:
- mutates world structures (rooms, doors, items, occupancy)
- emits WorldEvents for successful changes

### Phase G — Event Consolidation
Runtime:
- aggregates world events
- may add derived summary events (relationship/tension/etc.)
- stores them in history

### Phase H — Diff Recording + Snapshot
WorldSnapshot and diffs are built.
WorldEvents may inform snapshot/episode scene boundaries.

### Phase I — Narrative Trigger
Narrative reads snapshots/events; never writes commands/events.

---

## 7. Extension Rules
You may extend commands/events by:
- Adding new `WorldCommandKind` or `WorldEventKind` values
- Adding new ECS command kinds only if:
  - they map cleanly to ECS operations
  - they preserve archetype invariants

Any extension MUST:
- update this SOT with:
  - new kind name
  - required payload keys
  - semantics (effects + emitted events)
- remain deterministic and Rust-portable
- keep payload primitives-only

Forbidden:
- embedding arbitrary Python objects, LLM handles, file descriptors, or OS resources
- introducing free-text semantics in commands/events (semantic text belongs in narrative/integration UI)
- bypassing ECSWorld.apply_commands or WorldContext.apply_world_commands for mutations

---

## 8. Completion Conditions
This SOT is implemented and enforced when:
- `ecs/commands.py` defines:
  - `ECSCommand` and `ECSCommandKind` per §3
- `world/commands.py` defines:
  - `WorldCommand` and `WorldCommandKind` per §4
- `world/events.py` defines:
  - `WorldEvent` and `WorldEventKind` per §5
- ECSCommandBuffer (SOT-SIM4-ECS-SYSTEMS):
  - constructs only valid ECSCommand kinds
  - assigns deterministic seq indices
- WorldContext.apply_world_commands (or canonical applier):
  - accepts only valid WorldCommand kinds
  - emits WorldEvents consistent with this SOT
- Runtime:
  - routes commands/events strictly per Phase B–G
  - does not mutate ECS/world outside:
    - ECSWorld.apply_commands
    - WorldContext.apply_world_commands

At that point, the Sim4 command + event backbone is:
- small and well-specified
- easy to port to Rust
- safe for future architects to extend without semantic drift