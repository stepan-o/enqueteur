📘 SOT-SIM4-RUNTIME-WORLD-CONTEXT

WorldContext, World Commands & World Views (Runtime Façade)
Draft 1.1 — Architect-Level, Rust-Aligned

0. Scope & Purpose

This SOT defines the WorldContext façade in runtime/:

what WorldContext is and where it lives

how it orchestrates world subsystems in world/

how WorldCommands are applied to world state

how WorldViews are built and handed into ECS systems

how the runtime tick (SOP-200) talks to world without violating SOP-100

It is the canonical spec for:

runtime/world_context.py

its use of the world/ package:

world/identity/

world/graph/

world/layout/

world/rooms/

world/assets/

world/events.py

1. Position in the 6-Layer DAG

Per SOP-100 the DAG is:

runtime   →   ecs   →   world   →   snapshot   →   integration
↑
narrative (sidecar)


WorldContext is part of runtime/.

It sits at the runtime layer, not inside world/.

It holds references to:

the ECSWorld (from ecs/), as a read-only handle (no lifecycle or mutation),

the world subsystems (from world/), which it owns and orchestrates.

It never lives in world/, and world/ never imports ecs/.

So:

runtime.world_context may import world.* and ecs.*

world.* never imports ecs.* or runtime.*

ECS systems never import world.* – all world access is mediated via WorldViews created by WorldContext.

2. Responsibilities of Runtime WorldContext

WorldContext (runtime façade) is responsible for:

Owning and wiring world subsystems

constructs/owns:

WorldIdentity

RoomManager / RoomState

AssetManager / AssetState

NavGraph & layout structures

world state lives in world/ objects, but lifetime is coordinated by runtime.

Providing read-only WorldViews to ECS systems

builds PerceptionView, NavigationView, InteractionView each tick

passes them (via runtime/engine.py) to ECS systems during Phases B–E

Applying WorldCommands

takes structured WorldCommands from ecs-driven logic (collected by runtime)

applies them deterministically to world subsystems during Phase F

Emitting WorldEvents

converts applied WorldCommands + world changes into WorldEvents

returns them to runtime for consolidation and history logging

WorldContext does NOT:

store ECS component values itself

call narrative

perform I/O

introduce randomness (except via SimulationRNG provided by runtime)

3. Ownership & State Model
   3.1 Runtime vs World

Runtime (WorldContext):

owns the composition and the wiring:

references to RoomManager, AssetManager, NavGraph, etc.,

may hold a read-only reference to ECSWorld for view-building or cross-checks, but never mutates ECS state or manages ECS lifecycle.

orchestrates views + commands per tick.

World subsystems (world/ package):

own the actual world state:

room occupancy

asset statuses

navgraph dynamic flags

implement the low-level mutation and query logic.

This keeps world state in world/ while keeping orchestration in runtime/.

3.2 Construction

Runtime builds the WorldContext something like:

from world.identity import load_world_identity
from world.rooms import RoomManager
from world.assets import AssetManager
from world.graph import NavGraph

class WorldContext:
def __init__(...):
self.identity = load_world_identity(...)
self.rooms = RoomManager(...)
self.assets = AssetManager(...)
self.navgraph = NavGraph(...)
...


SimulationEngine holds a single WorldContext instance.

4. WorldCommands (Deterministic World Mutation API)

All world mutation happens via WorldCommands, applied only at Phase F of the tick (SOP-200).

4.1 Base Shape

Conceptually:

@dataclass(frozen=True)
class WorldCommand:
tick: int
sequence: int           # deterministic order within tick
kind: str               # "MoveAgent", "OpenDoor", ...
payload: dict           # schema-checked payload


Concrete types (likely in world/commands.py):

MoveAgent { agent_id, from_room, to_room }

SetAgentRoom { agent_id, room_id }

OpenDoor { door_id }

CloseDoor { door_id }

ToggleAsset { asset_id, mode }

SpawnItem { room_id or asset_id, item_id }

DespawnItem { item_id }

WorldFlagChange { key, value } (e.g. alarm_on: true)

4.2 WorldContext API

Runtime calls:

world_events = world_context.apply_commands(world_commands, dt, rng)


Rules:

world_commands is pre-sorted by (tick, sequence) by runtime.

apply_commands:

loops in stable order only

forwards each command to the appropriate world subsystem:

rooms, assets, navgraph, etc.

collects resulting WorldEvents (e.g. AgentMoved, DoorOpened, CommandFailed)

No ECS or narrative code is called during this.

5. WorldViews (Read-Only Inputs for ECS)

ECS systems may not import world/.
Instead, WorldContext builds views, and runtime passes them into systems.

5.1 PerceptionView

Used in Phase B (PerceptionSystem).

Contains per-room and per-agent read-only data:

room occupants (agent IDs)

neighboring rooms and edges

coarse distances/adjacency

simple environment flags (e.g. is_dark, is_crowded)

any occlusion or LOS info world provides

API:

perception_view = world_context.build_perception_view()

5.2 NavigationView

Used in movement resolution (Phase D/E, MovementResolutionSystem).

Contains:

navgraph nodes and edges (read-only snapshot)

edge costs / travel weights

blocked edges / closed doors

room-level tags as categorical codes

API:

nav_view = world_context.build_navigation_view()

5.3 InteractionView

Used in interaction resolution (Phase D/E, InteractionResolutionSystem).

Contains:

nearby agents per room

nearby assets + states

interaction affordances:

inspectable, openable, pickupable, useable etc.
(purely categorical codes, no semantics)

API:

interaction_view = world_context.build_interaction_view()

5.4 Future Views

Sim5+ may introduce additional view types:

TensionView, CrowdView, DistrictView, etc.

They must remain read-only, deterministic, and Rust-portable.

6. World Subsystems (world/ package)

WorldContext depends on pure world subsystems inside world/:

world/identity/

WorldIdentity, RoomIdentity, AssetIdentity

world/graph/

NavGraph, Links, SpatialIndex (optional)

world/layout/

LayoutSpec, CollisionMap (optional now, extended later)

world/rooms/

RoomState, RoomManager

world/assets/

AssetState, AssetManager

world/events.py

WorldEvent definitions

SOT for those lives in a separate “World Engine” SOT; here we only define how runtime.world_context uses them.

Key rules:

world subsystems never call ECS or runtime.

they expose methods such as:

room_manager.move_agent(...)

asset_manager.open_door(...)

navgraph.build_view(...)

all called through WorldContext.

7. Determinism & Rust Portability

WorldContext must obey SOP-200:

no Python random, no numpy.random, no time-based entropy

if randomness is needed for world selection:

use only the SimulationRNG passed in by runtime

iterate in stable order:

sort lists, deterministic key order, or explicit indices

never rely on dict/set iteration

The data passing across WorldContext must be:

simple dataclasses / dicts / lists

trivially mappable to Rust structs and Vecs

8. Integration with Runtime Tick Phases

Cross-check with runtime tick SOT:

Phase B — Perception
runtime.engine calls:

perception_view = world_context.build_perception_view()
ecs_systems.run_perception(perception_view)


Phase C — Cognition
Optional world-derived views may be built here, but still read-only.

Phase D/E — Intent & Action Resolution
runtime calls:

nav_view = world_context.build_navigation_view()
interaction_view = world_context.build_interaction_view()
ecs_systems.run_intent_and_actions(nav_view, interaction_view)


ECS systems emit WorldCommands into a buffer owned by runtime.

Phase F — World Updates
Runtime applies them:

world_events = world_context.apply_commands(world_commands, dt, rng)


Phase G/H/I

world_events go to runtime’s EventBus and HistoryBuffer.

snapshot/ queries world state via WorldContext or underlying world subsystems (read-only).

Narrative only sees world through snapshots/adapters.

9. Evolution Sim4 → SimX

This SOT is future-proof:

Sim4

small room graph

simple room/asset state

Sim5–Sim7

richer world state (tension fields, crowds, districts)

more complex WorldCommands but same façade

SimX

possibly multiple WorldContext or partitioned “WorldSegments” under a higher-level runtime orchestration; but:

WorldContext remains runtime-owned façade

world state remains in world/

ECS still only sees WorldViews

10. Completion Conditions

This SOT is implemented & respected when:

runtime/world_context.py exists and:

holds references to world subsystems

implements:

build_perception_view()

build_navigation_view()

build_interaction_view()

apply_commands(commands, dt, rng) -> list[WorldEvent]

Runtime tick uses those methods exactly in the right phases (B, D/E, F).

ECS systems receive only WorldViews, never import world/ directly.

world/ never imports ecs/ or runtime/.

All behavior is deterministic and Rust-portable.

Snapshots read world state through WorldContext and/or world subsystems read-only.

When these hold, WorldContext is correctly located in runtime/ and the world layer is SimX-safe.