📘 SOT-SIM4-WORLD-ENGINE

World Identities, Room/Asset State, NavGraph & World Events
Draft 1.0 — Architect-Level, Rust-Aligned, SOP-100/200/300 Compliant

0. Scope & Purpose

This SOT defines the world layer (world/) for Sim4:

What lives under world/ and what it is responsible for.

How world state is represented: rooms, assets, navgraph, layout.

How WorldCommands (from runtime/world_context.py) are applied as mutations.

How WorldEvents are emitted back to runtime.

How world state is exposed via WorldViews for ECS systems (through WorldContext).

It is aligned with and must not contradict:

SOP-100 — Layer Boundary Protection.

SOP-200 — Determinism & Simulation Contract.

SOT-SIM4-ENGINE — overall folder layout & layer responsibilities.

SOT-SIM4-RUNTIME-WORLD-CONTEXT — WorldContext façade & command/view contract.

SOT-SIM4-ECS-CORE, SOT-SIM4-ECS-SUBSTRATE-COMPONENTS, SOT-SIM4-ECS-SYSTEMS.

It does not define:

ECS components or systems (those live under ecs/ and are covered by ECS SOTs).

Narrative semantics or LLM outputs (narrative/).

Snapshot or episode schemas (snapshot/ + episode SOT).

This is the single source of truth for how the world layer behaves internally.

---

Sprint 5 Implementation Status (Sub‑Sprint 5.1–5.4)

Implemented (✅):
- WorldContext (backend/sim4/world/context.py):
  - Room registry: rooms_by_id: dict[RoomID, RoomRecord]
  - Agent ↔ Room indices: agent_room: dict[AgentID, RoomID], room_agents: dict[RoomID, set[AgentID]]
  - Item registry: items_by_id: dict[ItemID, ItemRecord] and per‑room index room_items: dict[RoomID, set[ItemID]]
  - Minimal door state: door_open: dict[DoorID, bool]
  - Helper methods: register_room/get_room, register_agent/move_agent/get_agent_room/get_room_agents, register_item/move_item/get_room_items, register_door/set_door_open/is_door_open
- World commands & events (backend/sim4/world/commands.py, backend/sim4/world/events.py):
  - WorldCommandKind: set_agent_room, spawn_item, despawn_item, open_door, close_door
  - WorldEventKind: agent_moved_room, item_spawned, item_despawned, door_opened, door_closed
  - Dataclasses are frozen and Rust‑portable.
- Canonical applier (backend/sim4/world/apply_world_commands.py):
  - apply_world_commands(world_ctx, commands): stable seq sort, mutates via WorldContext helpers, emits WorldEvent list.
  - Handles at minimum: SET_AGENT_ROOM, SPAWN_ITEM, OPEN_DOOR; optional: CLOSE_DOOR, DESPAWN_ITEM.
- Read‑only views (backend/sim4/world/views.py):
  - WorldViews façade and RoomView DTO, methods: get_agent_room, get_room_agents, get_room_items, is_door_open, get_room_view; iter_room_neighbors() is a stub that returns an empty tuple pending navgraph.

Deferred / TODO (⚠️):
- Runtime tick wiring (construction/injection of WorldViews, collection/dispatch of WorldCommands) — planned Sprint 6.
- NavGraph/neighbor topology; iter_room_neighbors remains a safe stub (returns ()).
- Snapshot/episode integration remains to be wired; events are generated but not yet persisted.

Public API Surface (for runtime) (ℹ️):
- from sim4.world import WorldContext, RoomRecord, ItemRecord, WorldCommand, WorldCommandKind, WorldEvent, WorldEventKind, apply_world_commands, WorldViews, RoomView
- Layer purity: world/ has no imports from ecs/ or runtime/; runtime will adapt and inject views.

1. Position in the 6-Layer DAG (SOP-100)
DAG (already locked):
```text
Kernel:   runtime → ecs → world
                \         \
                 \         → snapshot → integration
                  \
                   → (read-only views) → narrative
narrative → (suggestion queues) → runtime (Phase A integration ONLY)
```

Within this DAG:

world/ is a pure environment layer:

rooms, assets, navgraph, layout, world-level events.

world/:

never imports:

runtime/

ecs/

narrative/

snapshot/

integration/

operates only on IDs (EntityID, RoomID, AssetID, ItemID, DoorID, FactionID, …) and internal world structs.

runtime/world_context.py is the only owner of WorldContext, and it:

imports and owns world/ subsystems,

calls world methods to build WorldViews and apply WorldCommands,

returns WorldEvents to the runtime EventBus.

ECS systems never import world/ directly and only see world data via WorldViews (as specified in SOT-SIM4-RUNTIME-WORLD-CONTEXT).

2. Folder Layout for world/ (Sim4)

Canonical structure (must match SOT-SIM4-ENGINE):

world/
identity/
world_identity.py   # WorldIdentity
room_identity.py    # RoomIdentity
asset_identity.py   # AssetIdentity
npc_identity.py     # Optional prefab templates (IDs only)
graph/
navgraph.py         # NavGraph, NavNode, NavEdge
links.py            # Link definitions (room ↔ room, door info)
spatial_index.py    # Optional: SpatialIndex over rooms/assets
layout/
layout_spec.py      # LayoutSpec: room shapes, zones, tags
collision_map.py    # Optional: collision grids per room
rooms/
room_state.py       # RoomState (occupants, items, doors, flags)
room_manager.py     # RoomManager (API used by WorldContext)
assets/
asset_state.py      # AssetState (machine/prop state, item locations)
asset_manager.py    # AssetManager (API used by WorldContext)
events.py               # WorldEvent definitions
adapters.py             # Internal helper types for WorldViews
world_state.py          # WorldState root container (no ECS imports)


Notes:

WorldContext (in runtime) owns a WorldState instance and calls into RoomManager, AssetManager, NavGraph, etc.

WorldViews types (PerceptionView, NavigationView, InteractionView) are defined in world/adapters.py, used by runtime/world_context.py.

3. Identity Layer (world/identity/)

The identity layer is static metadata about the environment.
No ECS imports, no narrative data, no mutable gameplay state.

3.1 WorldIdentity (world_identity.py)

Shape (conceptual):

@dataclass(frozen=True)
class WorldIdentity:
world_id: int                 # enum/int code
version: int                  # schema/content version
seed: int                     # base RNG seed for world generation
room_ids: list[int]           # all RoomIDs present in world
asset_ids: list[int]          # all AssetIDs present at scenario start


Immutable during an episode.

Loaded by runtime at simulation startup.

3.2 RoomIdentity (room_identity.py)
RoomID = int   # or NewType[int, RoomID]

@dataclass(frozen=True)
class RoomIdentity:
id: RoomID
zone_code: int                # coarse region code (e.g. hallway, lab)
nav_node_id: int              # corresponding node in NavGraph
area_code: int                # optional: floor/wing ID
tag_codes: list[int]          # room tags as small ints (e.g. QUIET, PUBLIC)
capacity_hint: int            # coarse expected occupant count


No textual names or labels here (for Rust portability and semantics separation).

Human-readable names can exist in external content files, not in substrate.

3.3 AssetIdentity (asset_identity.py)
AssetID = int

@dataclass(frozen=True)
class AssetIdentity:
id: AssetID
type_code: int                # asset category (door, console, machine, decor)
default_room_id: RoomID       # spawn room
tag_codes: list[int]          # e.g. INTERACTABLE, DOOR, MACHINE
linked_room_id: RoomID | None # for doors/portals (room on other side)


Asset type and tags are int-coded enums, not strings.

3.4 NPCIdentity (npc_identity.py, optional for Sim4)

Optional static templates for NPC spawn logic; kept ID-based:

@dataclass(frozen=True)
class NPCIdentity:
template_id: int
default_room_id: RoomID
role_code: int          # matches AgentIdentity.role_code (int)
seed_offset: int        # for per-NPC RNG


Note: Actual NPC “mind” lives in ECS components. NPCIdentity is a spawn template only.

4. Navigation Graph & Layout (world/graph/, world/layout/)
   4.1 NavGraph (navgraph.py)

Core navigation substrate for MovementResolutionSystem & ActionExecutionSystem (via WorldContext views).

Conceptual types:

NodeID = int

@dataclass
class NavNode:
id: NodeID
room_id: RoomID
tag_codes: list[int]         # e.g. DOORWAY, CENTER, CORNER

@dataclass
class NavEdge:
id: int
from_node: NodeID
to_node: NodeID
base_cost: float
is_blocked: bool             # dynamic (e.g. closed door)
door_id: int | None          # link to door asset, if any


NavGraph:

@dataclass
class NavGraph:
nodes: dict[NodeID, NavNode]
edges: dict[int, NavEdge]
# Optional adjacency indexes


Allowed methods (shape-level):

neighbors(node_id) -> Iterable[NavEdge]

mark_edge_blocked(edge_id, blocked: bool)

shortest_path(from_node, to_node) -> list[NodeID] (deterministic).

4.2 Links & Spatial Index (links.py, spatial_index.py)

links.py:

Encodes static door/portal relationships between rooms.

spatial_index.py (optional, for Sim4 can be stub):

Provides coarse spatial queries like “assets in room”, “assets near node”.

Must obey determinism:

No random tie-breaking for equal-cost paths; use a deterministic rule (e.g. smallest edge/room ID).

4.3 Layout Spec & Collision (layout_spec.py, collision_map.py)

Optional but future-proof:

@dataclass
class LayoutSpec:
room_id: RoomID
width: float
height: float
# optional grid / zones

@dataclass
class CollisionMap:
room_id: RoomID
grid: list[list[int]]  # collision codes


LayoutSpec & CollisionMap must be read-only from the perspective of ECS; only world subsystems mutate them if absolutely needed (e.g. dynamic obstacles).

5. Room State & RoomManager (world/rooms/)
   5.1 RoomState (room_state.py)
   @dataclass
   class RoomState:
   room_id: RoomID
   occupant_ids: list[int]        # EntityID
   item_ids: list[int]            # ItemID
   door_ids: list[int]            # DoorID, linking to AssetState
   is_dark: bool
   is_crowded: bool               # optional derived metric
   ambient_noise_level: float     # 0–1 or scalar


Notes:

No ECS component instances here, only IDs.

Room flags (is_dark, is_crowded) are numeric/boolean and can be derived from internal logic (e.g. occupant count thresholds).

5.2 RoomManager (room_manager.py)

RoomManager owns and mutates all RoomState instances.

Conceptual:

class RoomManager:
def __init__(self, identities: list[RoomIdentity]):
...

    def get_room_state(self, room_id: RoomID) -> RoomState: ...

    def move_agent(self, agent_id: int, from_room: RoomID | None, to_room: RoomID) -> None: ...

    def add_item_to_room(self, item_id: int, room_id: RoomID) -> None: ...
    def remove_item_from_room(self, item_id: int, room_id: RoomID) -> None: ...

    def update_room_flags(self, room_id: RoomID) -> None:
        # recompute is_crowded, etc. deterministically
        ...


Constraints:

No ECS imports.

Deterministic behavior:

occupant_ids and item_ids ordering is stable (e.g. insertion order with explicit rules).

No dict/set iteration without sorting.

RoomManager is invoked only by WorldContext when applying commands or building views.

6. Asset State & AssetManager (world/assets/)
   6.1 AssetState (asset_state.py)
   ItemID = int
   DoorID = int

@dataclass
class AssetState:
asset_id: AssetID
room_id: RoomID
status_code: int          # generic enum: OFF/ON, CLOSED/OPEN, IDLE/ACTIVE
mode_code: int            # more specific state (machine mode, door locked, etc.)
linked_item_ids: list[ItemID]
linked_room_id: RoomID | None  # for doors/portals


status_code and mode_code are int-coded enums, not strings.

6.2 AssetManager (asset_manager.py)

Conceptual:

class AssetManager:
def __init__(self, identities: list[AssetIdentity]):
...

    def get_asset_state(self, asset_id: AssetID) -> AssetState: ...

    def toggle_asset(self, asset_id: AssetID, new_status_code: int) -> None: ...
    def set_mode(self, asset_id: AssetID, new_mode_code: int) -> None: ...

    def move_item_between_assets(self, item_id: ItemID, from_asset: AssetID, to_asset: AssetID) -> None: ...


Rules:

Deterministic, no randomness.

Does not know about ECS or narrative; just asset mechanics.

7. World Events (world/events.py)

WorldEvents are emitted by world subsystems when commands are applied (Phase F) and consumed by runtime for logging/history.

Conceptual base:

@dataclass(frozen=True)
class WorldEvent:
tick: int
kind: str       # "AgentMoved", "DoorOpened", "AssetToggled", ...
payload: dict   # simple, Rust-portable values only


Canonical Sim4 events (minimum set):

AgentMoved

payload: { "agent_id": int, "from_room": RoomID | None, "to_room": RoomID }

DoorOpened, DoorClosed

payload: { "door_id": DoorID, "room_id": RoomID }

AssetToggled

payload: { "asset_id": AssetID, "status_code": int }

ItemSpawned, ItemDespawned

payload: { "item_id": ItemID, "room_id": RoomID | None, "asset_id": AssetID | None }

CommandFailed

payload: { "command_kind": str, "reason_code": int }

WorldEvents:

are created in response to WorldCommands,

never reference ECS components directly,

are Rust-portable and deterministic.

8. WorldState Root (world/world_state.py)

WorldState is a pure container for world subsystems, with optional helpers.
WorldContext (runtime) owns exactly one WorldState instance.

Conceptual:

@dataclass
class WorldState:
identity: WorldIdentity
rooms: "RoomManager"
assets: "AssetManager"
navgraph: "NavGraph"
layout_specs: dict[RoomID, "LayoutSpec"]
collision_maps: dict[RoomID, "CollisionMap"] | None


Rules:

WorldState does not import ECS or runtime.

It may provide helper methods (all deterministic), but the primary mutation orchestration remains in runtime/world_context.py per SOT-SIM4-RUNTIME-WORLD-CONTEXT.

If desired, Sim4 may add:

    def apply_world_command(self, cmd: WorldCommand, dt: float, rng: SimulationRNG) -> list[WorldEvent]:
        # Called by WorldContext as an internal helper
        ...


…but the external contract remains:

Runtime calls WorldContext.apply_commands().

WorldContext decides whether to delegate to WorldState.apply_world_command() or call managers directly.

9. World Adapters & View Types (world/adapters.py)

This module defines the structural shapes of the read-only views that WorldContext builds and passes to ECS systems, as specified in SOT-SIM4-RUNTIME-WORLD-CONTEXT.

9.1 PerceptionView

Used in Phase B by PerceptionSystem.

Conceptual:

@dataclass
class PerceptionView:
# indexed by RoomID
room_occupants: dict[RoomID, list[int]]        # EntityID list
room_items: dict[RoomID, list[ItemID]]
room_flags: dict[RoomID, dict[str, int | float | bool]]
# visibility matrix (optional coarse representation)
visible_rooms_from: dict[RoomID, list[RoomID]]


WorldContext.build_perception_view():

reads from WorldState.rooms, WorldState.navgraph, etc.

returns PerceptionView for ECS usage.

9.2 NavigationView

Used in Phase D/E by MovementResolutionSystem and ActionExecutionSystem.

@dataclass
class NavigationView:
nav_nodes: dict[int, NavNode]          # NodeID → NavNode
nav_edges: dict[int, NavEdge]          # EdgeID → NavEdge
room_to_node_ids: dict[RoomID, list[int]]


Optional helper methods can exist on the view, but all must be:

deterministic,

free of randomness and I/O.

9.3 InteractionView

Used in Phase D/E by InteractionResolutionSystem (and optionally InventorySystem).

@dataclass
class InteractionView:
agents_in_room: dict[RoomID, list[int]]      # EntityID list
assets_in_room: dict[RoomID, list[AssetID]]
asset_states: dict[AssetID, AssetState]      # shallow snapshots, no methods


Views must:

contain snapshots of world state for the current tick (no lazy links back),

be read-only from ECS systems’ perspective (they must not mutate world via these objects).

10. Determinism & Rust Portability (World Layer)

The world engine must obey the same determinism constraints as ECS:

No direct use of random or time-based APIs.

If randomness is needed (e.g. to break ties in path planning):

use only the SimulationRNG passed in by runtime/WorldContext,

use stable, documented rules for tie-breaking (e.g. smallest RoomID, NodeID).

Data types must map trivially to Rust:

Lists ↔ Vec<T>,

Dicts ↔ HashMap/BTreeMap (with explicit ordering rules),

Dataclasses ↔ Rust structs.

Forbidden:

dynamic attribute injection,

Python-only magic,

references to ECS / runtime / narrative types.

11. Extension Rules (Sim5+)

You may extend world/ by:

Adding new WorldCommand kinds (but must be documented in a commands/events SOT).

Adding new world subsystems (e.g. tension fields, districts, crowd layers).

Adding new view types (e.g. TensionView, CrowdView) exposed via WorldContext.

You must not:

introduce any import from ecs/, runtime/, narrative/, snapshot/, integration/ into world/,

embed narration or semantics as free text in world state,

use nondeterministic behavior.

Major changes require SOT revision and a note on Rust migration impact.

12. Completion Conditions for SOT-SIM4-WORLD-ENGINE

This SOT is considered implemented and enforced when:

world/ directory matches the layout in §2.

Identity, graph, layout, rooms, and assets modules:

use only Rust-portable dataclasses and primitives,

have no ECS, runtime, or narrative imports.

WorldState exists and aggregates:

WorldIdentity, RoomManager, AssetManager, NavGraph, layout data.

RoomManager and AssetManager:

own RoomState / AssetState,

expose deterministic methods called only by WorldContext.

world/events.py defines world events that:

are emitted only when commands are applied,

are stored as simple, deterministic structs.

world/adapters.py defines:

PerceptionView, NavigationView, InteractionView types,

used by runtime/world_context.py to implement:

build_perception_view(),

build_navigation_view(),

build_interaction_view() (per SOT-SIM4-RUNTIME-WORLD-CONTEXT).

No module in world/:

imports or references ECS components,

calls systems, narrative, or snapshot code.

At that point, the world engine is:

Sim4-correct as an environment layer,

SimX-ready for richer worlds and Rust porting,

and fully aligned with the locked runtime/ECS SOTs.