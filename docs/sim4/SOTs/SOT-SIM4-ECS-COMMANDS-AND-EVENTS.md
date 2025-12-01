📘 SOT-SIM4-ECS-COMMANDS-AND-EVENTS

ECSCommand, WorldCommand, WorldEvent
Draft 1.0 — Architect-Level, Rust-Aligned, SOP-100/200/300 Compliant

0. Scope & Purpose

This SOT unifies and locks the Sim4 command/event vocabulary used by:

ECS (substrate + systems),

World Engine / WorldContext,

Runtime tick & history.

It defines:

The canonical schema for:

ECSCommand

WorldCommand

WorldEvent

The allowed kind values for:

ECSCommand.kind

WorldCommand.kind

core WorldEvent.kind

How commands & events are:

constructed by systems/runtime,

applied by ECSWorld and WorldContext,

surfaced to snapshot / narrative / frontend.

It ties together:

SOT-SIM4-ECS-CORE (ECSWorld + apply_commands),

SOT-SIM4-ECS-SYSTEMS (who emits what),

SOT-SIM4-WORLD-ENGINE (WorldContext, WorldCommand, WorldEvent),

SOT-SIM4-RUNTIME-TICK (phase sequencing),

SOT-SIM4-SNAPSHOT-AND-EPISODE (event-based summaries).

This doc is the single source of truth for ECS + world command/event types and kind enums.

1. Position in the 6-Layer DAG

DAG reminder:

runtime   →   ecs   →   world   →   snapshot   →   integration
↑
narrative (sidecar)


Commands & events sit on the edges:

ECS layer

ECSCommand is consumed by ECSWorld.apply_commands() (Phase E).

ECSCommand is only created by:

ECS systems (via ECSCommandBuffer),

runtime bootstrapping (initial entity creation).

World layer

WorldCommand is consumed by WorldContext.apply_world_commands() (Phase F).

WorldEvent is emitted by the world engine as it applies world commands and reacts to ECS state.

Runtime

Owns the buffers and sequencing:

collects ECSCommands and WorldCommands from systems,

runs ECSWorld.apply_commands then WorldContext.apply_world_commands,

aggregates WorldEvents into history and narratives.

Constraints:

ECS never directly mutates WorldContext.

WorldContext never directly mutates ECSWorld.

Narrative never issues raw ECSCommand / WorldCommand; it influences via substrate (e.g. PrimitiveIntent) and high-level hooks.

2. Folder Layout & Ownership

Canonical locations:

ecs/
commands.py     # ECSCommand, ECSCommandKind (string constants / enum)
...             # ecs/world.py, ecs/entity.py, etc.

world/
commands.py     # WorldCommand, WorldCommandKind
events.py       # WorldEvent, WorldEventKind

runtime/
command_bus.py  # (optional) Command buffers, routing, sequencing


Ownership:

ecs/commands.py belongs to the ECS layer.

world/commands.py and world/events.py belong to the world layer.

Runtime uses these types but does not redefine them.

3. ECSCommand Schema
   3.1 Core Type

Shape-level dataclass (Python):

# ecs/commands.py

from dataclasses import dataclass
from typing import Any, Optional

EntityID = int  # as per SOT-SIM4-ECS-CORE

@dataclass(frozen=True)
class ECSCommand:
seq: int                      # stable sequence index within the tick
kind: str                     # one of ECSCommandKind.*
entity_id: Optional[EntityID] # target entity (if applicable)

    # Component targeting
    component_type: Optional[type]  # Python prototype (maps to type-code in Rust)
    component_type_code: Optional[int]  # SimX/Rust: canonical type ID

    # Payload variants (see kinds below)
    component_instance: Any | None      # full dataclass instance
    field_name: Optional[str]
    value: Any | None

    # Entity creation
    archetype_code: Optional[int]
    initial_components: Optional[list[Any]]


Portability:

In Python prototype, either component_type or component_type_code may be primary.

In Rust, component_type_code is the canonical field; Python type is a convenience only.

3.2 ECSCommandKind

ECSCommand.kind is a string enum with a fixed core set:

class ECSCommandKind:
SET_FIELD       = "set_field"
SET_COMPONENT   = "set_component"
ADD_COMPONENT   = "add_component"
REMOVE_COMPONENT= "remove_component"
CREATE_ENTITY   = "create_entity"
DESTROY_ENTITY  = "destroy_entity"


Semantics:

CREATE_ENTITY

Fields used:

entity_id: None (ID allocated by ECSWorld).

archetype_code: optional hint for initial archetype.

initial_components: list of component instances.

Effect:

ECSWorld allocates a new EntityID.

Attaches initial_components.

Places entity into appropriate archetype storage.

DESTROY_ENTITY

Fields:

entity_id: required.

Effect:

ECSWorld removes all components.

Removes entity from archetype storage.

Marks ID as dead (optional recycling policy per SOT-ECS-CORE).

ADD_COMPONENT

Fields:

entity_id: required.

component_instance: full dataclass instance of a new component.

component_type / component_type_code inferred from instance if not explicit.

Effect:

If the entity lacks this component type:

Attach component.

Move entity into new archetype signature.

If it already has one:

Behavior is implementation-defined; Sim4 convention:

treat as error in debug builds,

or fall back to SET_COMPONENT semantics.

Must be documented in code-level docstrings.

REMOVE_COMPONENT

Fields:

entity_id: required.

component_type or component_type_code: required.

Effect:

Remove component of that type (if present).

Move entity into new archetype storage.

If missing:

No-op or debug warning; must be deterministic.

SET_COMPONENT

Fields:

entity_id: required.

component_instance: full replacement instance.

Effect:

If component exists:

Replace its stored value with component_instance.

If component does not exist:

Implementation choice:

either implicitly add (like ADD_COMPONENT),

or treat as error/no-op.

Sim4 recommendation: add if missing for ergonomic system code, but document.

SET_FIELD

Fields:

entity_id: required.

component_type or component_type_code: required.

field_name: required.

value: new scalar/struct value.

Effect:

Mutate only the named field on the component instance.

Does not change archetype signature.

If field or component is missing:

deterministic no-op or debug error, never undefined behavior.

3.3 Deterministic Application

Per SOT-SIM4-ECS-CORE:

ECSWorld.apply_commands(commands: Iterable[ECSCommand]) must:

sort/process by seq if necessary,

apply each command exactly once,

maintain archetype invariants.

All ECS systems (per SOT-ECS-SYSTEMS) must:

create commands via ECSCommandBuffer, which:

assigns increasing seq numbers,

ensures stable order per system & tick.

4. WorldCommand Schema
   4.1 Core Type

World commands express environment-level changes that cannot be handled purely inside ECS (room occupancy lists, door state, item spawn/despawn, etc.).

# world/commands.py

from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class WorldCommand:
seq: int                 # global sequence within the tick
kind: str                # one of WorldCommandKind.*
tick_index: int          # tick at which it was issued

    actor_agent_id: Optional[int]  # agent causing this, if any
    room_id: Optional[int]         # primary room context, if any

    payload: dict[str, Any]        # kind-specific fields (see below)


Rules:

World commands are write-only from the world engine’s perspective:

consumed by WorldContext.apply_world_commands(commands) (Phase F).

They are constructed by:

ECS systems (via ctx.commands.emit_world_command),

runtime (bootstrapping world state).

4.2 WorldCommandKind

Core Sim4 set (minimal but sufficient):

class WorldCommandKind:
# Agent placement & movement (world-side)
SET_AGENT_ROOM   = "set_agent_room"
MOVE_AGENT_PATH  = "move_agent_path"

    # Doors / portals
    OPEN_DOOR        = "open_door"
    CLOSE_DOOR       = "close_door"

    # Items / inventory in world space
    SPAWN_ITEM       = "spawn_item"
    DESPAWN_ITEM     = "despawn_item"
    SET_ITEM_ROOM    = "set_item_room"
    SET_ITEM_OWNER   = "set_item_owner"

    # Room/world state
    SET_ROOM_STATE   = "set_room_state"
    TAG_ROOM         = "tag_room"
    TAG_AGENT        = "tag_agent"


Semantics & payloads:

SET_AGENT_ROOM

Purpose: update world-level occupancy lists when an agent changes rooms.

Payload:

{
"agent_id": int,
"from_room_id": Optional[int],
"to_room_id": int,
}


Effect:

Update Room occupants sets in WorldContext.

Must be consistent with ECS transform/RoomPresence (ECS side handled by ActionExecutionSystem).

MOVE_AGENT_PATH

Purpose: optional high-level command if world handles coarse navigation.

Payload:

{
"agent_id": int,
"room_sequence": list[int],   # room_ids
}


Effect:

World engine may:

validate path,

schedule or apply multiple SET_AGENT_ROOM internally.

Useful if we later externalize pathfinding.

OPEN_DOOR / CLOSE_DOOR

Payload:

{
"door_id": int,
}


Effect:

Mutate door state within WorldContext.

May emit WorldEvents like door_opened / door_closed.

SPAWN_ITEM

Payload:

{
"item_id": int,          # or None if world allocates
"room_id": Optional[int],
"owner_agent_id": Optional[int],
"item_kind_code": int,   # enum-coded logical type
}


Effect:

Create world-level record for an item.

Place it into room and/or associate with owner.

Emit item_spawned event.

DESPAWN_ITEM

Payload:

{
"item_id": int,
}


Effect:

Remove world-level record.

Emit item_despawned.

SET_ITEM_ROOM

Payload:

{
"item_id": int,
"from_room_id": Optional[int],
"to_room_id": Optional[int],
}


Effect:

Move item between rooms (or to/from “no-room” state).

SET_ITEM_OWNER

Payload:

{
"item_id": int,
"from_owner_agent_id": Optional[int],
"to_owner_agent_id": Optional[int],
}


Effect:

Transfer item ownership; world-level mirror of ECS Inventory changes.

SET_ROOM_STATE

Payload:

{
"room_id": int,
"state_code": int,        # enum-coded (e.g., DIM_LIGHTS, LOCKDOWN)
}


Effect:

Mutate world-level room state.

Can feed into perception/world-views.

TAG_ROOM / TAG_AGENT

Payload:

{
"room_id": int,                 # for TAG_ROOM
"agent_id": int,                # for TAG_AGENT
"tag_code": int,                # enum-coded
}


Effect:

Lightweight world-level tagging for:

debug overlays,

narrative hints,

snapshot decorations.

Purely structural; no semantic strings here.

5. WorldEvent Schema
   5.1 Core Type

World events are facts produced by the world engine (and optionally ECS diff summarization) that:

feed:

runtime history,

snapshot/episode builders,

narrative contexts.

# world/events.py

from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class WorldEvent:
tick_index: int
kind: str                     # one of WorldEventKind.*
importance: float             # 0..1, narrative/useful hint

    actor_agent_id: Optional[int]
    target_agent_id: Optional[int]
    room_id: Optional[int]
    item_id: Optional[int]

    payload: dict[str, Any]       # kind-specific details


Rules:

Events are append-only:

emitted during Phase F / G,

stored in history buffers,

used by snapshot diff + narrative, never mutated in-place.

Importance is:

numeric hint for down-stream consumers (snapshot/episode builder, narrative),

not used by substrate.

5.2 WorldEventKind

We define a core set; additional kinds may be added with SOT updates.

class WorldEventKind:
# Movement & presence
AGENT_MOVED           = "agent_moved"
AGENT_ENTERED_ROOM    = "agent_entered_room"
AGENT_LEFT_ROOM       = "agent_left_room"

    # Doors / portals
    DOOR_OPENED           = "door_opened"
    DOOR_CLOSED           = "door_closed"

    # Items / inventory
    ITEM_SPAWNED          = "item_spawned"
    ITEM_DESPAWNED        = "item_despawned"
    ITEM_PICKED_UP        = "item_picked_up"
    ITEM_DROPPED          = "item_dropped"
    ITEM_EQUIPPED         = "item_equipped"
    ITEM_UNEQUIPPED       = "item_unequipped"

    # Interactions
    INTERACTION_COMPLETED = "interaction_completed"

    # Social / emotional summaries (derived)
    RELATIONSHIP_CHANGED  = "relationship_changed"
    TENSION_SPIKE         = "tension_spike"

    # Debug / meta markers
    TICK_MARKER           = "tick_marker"


Recommended payloads:

AGENT_MOVED

{
"agent_id": int,
"from_room_id": Optional[int],
"to_room_id": int,
}


AGENT_ENTERED_ROOM / AGENT_LEFT_ROOM

{
"agent_id": int,
"room_id": int,
}


DOOR_OPENED / DOOR_CLOSED

{
"door_id": int,
"room_a_id": int,
"room_b_id": int,
}


ITEM_SPAWNED / ITEM_DESPAWNED

{
"item_id": int,
"room_id": Optional[int],
"owner_agent_id": Optional[int],
"item_kind_code": int,
}


ITEM_PICKED_UP / ITEM_DROPPED / ITEM_EQUIPPED / ITEM_UNEQUIPPED

{
"agent_id": int,
"item_id": int,
"from_room_id": Optional[int],     # for pick/drop, if relevant
"to_room_id": Optional[int],
"slot_code": Optional[int],        # for equip/unequip
}


INTERACTION_COMPLETED

{
"interaction_kind_code": int,   # enum (TALK, HELP, ARGUE, etc. numeric)
"success": bool,
"actor_agent_id": int,
"target_agent_id": Optional[int],
}


RELATIONSHIP_CHANGED (from social/ECS summarizer, not world engine itself)

{
"agent_a_id": int,
"agent_b_id": int,
"delta": float,          # signed change
"new_value": float,      # current relationship [-1, 1]
}


TENSION_SPIKE

{
"room_id": int,
"old_tension": float,
"new_tension": float,
}


TICK_MARKER

{
"label": str,            # short debug / structural label
}


Note: Social/emotional events (7–8) are conceptually emitted by a summarization pass that reads ECS after Phase E & F (Phase G), not by the world engine’s physics directly. They still share the WorldEvent schema.

6. Integration with Tick Phases

Per SOT-SIM4-RUNTIME-TICK:

Phases B–D (ECS systems)

Systems read ECS state + WorldViews and write into:

ECSCommandBuffer → list of ECSCommand

WorldCommand buffer → list of WorldCommand

All commands get monotonic seq indices.

Phase E — ECS Command Application

Runtime calls: ECSWorld.apply_commands(ecs_commands).

ECSWorld:

applies CREATE_ENTITY, DESTROY_ENTITY, ADD_COMPONENT, REMOVE_COMPONENT, SET_COMPONENT, SET_FIELD.

updates archetype storage deterministically.

Phase F — World Command Application

Runtime calls: WorldContext.apply_world_commands(world_commands).

World engine:

mutates internal world structures (rooms, doors, item registries, occupancy, etc.),

emits WorldEvents as changes occur.

Phase G — Event Consolidation

Runtime:

aggregates WorldEvents,

may add derived summary events (e.g. RELATIONSHIP_CHANGED, TENSION_SPIKE),

stores them in history.

Phase H — Diff Recording + Snapshot

WorldSnapshot and diff are built.

WorldEvents are available for snapshot/episode builders to:

segment scenes,

mark key frames.

Phase I — Narrative Trigger

NarrativeRuntimeContext constructs:

NarrativeTickContext from:

latest WorldSnapshot,

WorldEvents for the tick,

agent-focused slices.

Narrative reads but never writes commands/events.

7. Extension Rules

You may extend commands/events by:

Adding new WorldCommandKind or WorldEventKind constants.

Adding new ECSCommand kinds only if:

they map cleanly to ECS operations,

they don’t bypass archetype invariants.

Any extension must:

Update this SOT with:

new kind name,

expected payload keys,

semantics.

Remain:

deterministic,

Rust-portable,

layer-pure (no narrative/OS handles inside payloads).

Forbidden:

Embedding arbitrary Python objects, LLM handles, file descriptors, etc. inside payloads.

Using free-text semantics in a way that breaks substrate rules (semantic strings belong in narrative, not commands/events).

8. Completion Conditions for SOT-SIM4-ECS-COMMANDS-AND-EVENTS

This SOT is considered implemented and enforced when:

ecs/commands.py defines:

ECSCommand with fields as per §3.1,

ECSCommandKind with values as per §3.2.

world/commands.py defines:

WorldCommand and WorldCommandKind as per §4.

world/events.py defines:

WorldEvent and WorldEventKind as per §5.

ECSCommandBuffer (from SOT-ECS-SYSTEMS):

constructs only valid ECSCommand kinds,

assigns deterministic seq indices.

WorldContext.apply_world_commands:

accepts only valid WorldCommand.kind values,

emits WorldEvent according to this SOT.

Runtime:

routes commands and events strictly according to Phase B–G,

does not mutate ECS or world outside of:

ECSWorld.apply_commands,

WorldContext.apply_world_commands.

At that point, the command + event backbone of Sim4 is:

small and well-specified,

easy to port to Rust,

and safe for future architects to extend without semantic drift.