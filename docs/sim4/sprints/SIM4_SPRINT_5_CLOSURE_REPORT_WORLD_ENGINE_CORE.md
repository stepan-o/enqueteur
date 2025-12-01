Sprint 5 — World Engine Core

Completion / Closure Report

Sprint Goal
Establish a deterministic, ECS-agnostic world engine substrate with clear commands, events, and read-only views, so that the runtime tick (Sprint 6) can wire ECS + world together without touching world internals.

1. Scope Recap

Planned sprint scope:

5.1 – Data-only WorldContext substrate (rooms/agents/items).

5.2 – WorldCommand & WorldEvent types.

5.3 – apply_world_commands + state mutation & event emission.

5.4 – WorldViewsHandle / read-only views for ECS/runtime.

5.5 – Integration pass, cleanup, docs & implementation report updates.

2. Delivered Work (by Sub-Sprint)
   5.1 — Core WorldContext Substrate

Files

backend/sim4/world/context.py

backend/sim4/tests/world/test_world_context.py

Key Deliverables

ID aliases: RoomID, AgentID, ItemID, DoorID.

Registries:

rooms_by_id: dict[RoomID, RoomRecord]

agent_room: dict[AgentID, RoomID]

room_agents: dict[RoomID, set[AgentID]]

items_by_id: dict[ItemID, ItemRecord]

room_items: dict[RoomID, set[ItemID]]

door_open: dict[DoorID, bool]

Helpers:

register_room, get_room

register_agent, move_agent, get_agent_room, get_room_agents

register_item, move_item, get_room_items

register_door, set_door_open, is_door_open

Behavior:

Deterministic and Rust-portable (ints, bools, dataclasses).

Explicit error conditions for invalid IDs / duplicate registration.

Tests cover basic registry and invariants.

5.2 — WorldCommand & WorldEvent Types

Files

backend/sim4/world/commands.py

backend/sim4/world/events.py

backend/sim4/tests/world/test_world_commands_events.py

Key Deliverables

Command enum WorldCommandKind:

set_agent_room, spawn_item, despawn_item, open_door, close_door.

Event enum WorldEventKind:

agent_moved_room, item_spawned, item_despawned, door_opened, door_closed.

Frozen, Rust-portable dataclasses:

WorldCommand with seq, kind, and optional ID/payload fields.

WorldEvent with kind, IDs, and previous_room_id where relevant.

Helper constructors (e.g. make_set_agent_room, make_spawn_item, etc.).

Tests assert:

Enum value stability.

Dataclass immutability.

Helper constructors produce expected shapes.

5.3 — apply_world_commands & Event Emission

Files

backend/sim4/world/apply_world_commands.py

backend/sim4/world/context.py (extensions)

backend/sim4/tests/world/test_apply_world_commands.py

Key Deliverables

Canonical applier:

apply_world_commands(world_ctx, commands) -> list[WorldEvent]

Optional convenience method WorldContext.apply_world_commands(...).

Behavior:

Collects commands, sorts by seq (stable, deterministic).

Dispatches on WorldCommandKind using WorldContext helpers.

Emits a WorldEvent per successful mutation.

Implemented handlers:

SET_AGENT_ROOM → AGENT_MOVED_ROOM (with previous_room_id).

SPAWN_ITEM → ITEM_SPAWNED.

DESPAWN_ITEM → ITEM_DESPAWNED.

OPEN_DOOR → DOOR_OPENED.

CLOSE_DOOR → DOOR_CLOSED.

Door support added to WorldContext:

DoorID alias.

door_open registry.

register_door, set_door_open, is_door_open.

Tests cover:

Correct state mutation and event emission.

Ordering determinism via seq.

Error behavior (no events on failed mutation).

5.4 — WorldViews Read-only Façade

Files

backend/sim4/world/views.py

backend/sim4/world/context.py (adds .make_views())

backend/sim4/tests/world/test_world_views.py

Key Deliverables

WorldViews (read-only façade):

Wraps a WorldContext, exposes only safe queries:

get_agent_room(agent_id) -> Optional[RoomID]

get_room_agents(room_id) -> FrozenSet[AgentID]

get_room_items(room_id) -> FrozenSet[ItemID]

is_door_open(door_id) -> bool

get_room_view(room_id) -> RoomView

iter_room_neighbors(room_id) -> Iterable[RoomID] (currently returns () with a TODO for navgraph).

RoomView DTO:

Frozen dataclass capturing room id + immutable collections of agents/items.

WorldContext.make_views():

Factory to produce a WorldViews instance, to be injected into SystemContext.views via runtime.

Tests verify:

Views reflect world state after commands.

Returned collections are immutable and not aliased to internal sets.

Error propagation behavior is consistent with WorldContext.

5.5 — Public API, Docs Alignment, Implementation Report

Files

backend/sim4/world/__init__.py

docs/sim4/SOTs/SOT-SIM4-WORLD-ENGINE.md

docs/sim4/SOTs/SOT-SIM4-ECS-COMMANDS-AND-EVENTS.md

docs/sim4/dev/reports/2025-12-01_sim4_ecs_implementation_overview.md

Key Deliverables

Public API (sim4.world)
Exported via __all__:

WorldContext

RoomRecord, ItemRecord

WorldCommand, WorldCommandKind

WorldEvent, WorldEventKind

apply_world_commands

WorldViews, RoomView

This is the surface runtime should import from in Sprint 6.

Consistency & SOT alignment

Verified that:

Command/event enum names and string values match SOT(s).

Dataclass field sets & semantics match the SOT descriptions.

No behavior changes; only naming/documentation tightening.

SOT updates

SOT-SIM4-WORLD-ENGINE:

Added “Sprint 5 Implementation Status” with:

✅ Implemented: WorldContext, commands/events, applier, views.

⚠️ Deferred: navgraph, neighbor topology, snapshot/episode wiring, runtime tick integration.

Clarified the world public API surface and layer purity.

SOT-SIM4-ECS-COMMANDS-AND-EVENTS:

Updated to reflect canonical WorldCommandKind/WorldEventKind.

Documented the actual Python dataclass shapes.

Implementation report extension

Existing report (ECS overview) extended with:
“2) World Engine Implementation (Sprint 5)”:

Overview of WorldContext, commands/events, applier, WorldViews.

Spec alignment summary vs world & commands/events SOTs.

Known Gaps / TODO[WORLD] and “Ready for Sprint 6 (Runtime Tick)” section explicitly stating:

What runtime can rely on.

What runtime must provide.

What is still stubbed (navgraph, snapshot wiring, etc.).

3. Alignment Check vs Upcoming Sprints
   For Sprint 6 — Runtime Tick Pipeline

Runtime will need:

A world substrate that can:

Be constructed and owned by runtime.

Apply batches of WorldCommand deterministically.

Emit WorldEvent instances for history/snapshot.

Expose a WorldViews-shaped object that satisfies the WorldViewsHandle Protocol used in ecs/systems/base.py.

✅ Status: All of these contracts exist:

WorldContext & apply_world_commands are implemented.

WorldCommand, WorldEvent + enums are stable and SOT-aligned.

WorldViews + RoomView satisfy the read-only views need.

Public imports are available via from sim4.world import ....

Remaining work for Sprint 6 is legitimately runtime-side:

Implement tick phases A–I.

Wire SystemContext.views to a WorldViews instance.

Aggregate ECS and world commands and apply them in the right phases.

Consolidate events.

No changes to world/ are blocking Sprint 6.

For Sprint 7 — Snapshot & Episode Types

Snapshot builder will need:

Access to ECSWorld and WorldContext + optionally WorldEvents.

Stable public API from sim4.world for world state querying.

✅ The world side is ready:

WorldContext & WorldViews provide deterministic queries.

World events have stable shapes and kinds.

Snapshot work can build directly on these without modifying world.

For Sprint 8 — Narrative Runtime Context & Interface

Narrative will primarily interact with:

Snapshots and/or DTOs provided by runtime.

Narrative interface & runtime contexts (narrative layer).

The world layer only needs to be deterministic and ID-based — which is already the case. No extra world changes are required to unblock Sprint 8.

4. Known Gaps (Non-Blocking for Sprint 6)

Documented gaps (also captured in SOT + implementation report):

NavGraph / room neighbors:

iter_room_neighbors() is a safe stub returning ().

Pathfinding, door-based edge blocking, etc., are not implemented yet.

Snapshot & episode integration:

No world → snapshot wiring; events are produced but not persisted.

Runtime orchestration:

Tick, command buses, event buses are not implemented yet (by design; this is Sprint 6 scope).

WorldState / managers:

The more elaborate WorldState, RoomManager, AssetManager, navgraph, etc., described later in the SOT exist as a future expansion path, not as Sprint 5 scope.

Implementation status is clearly called out in the “Sprint 5 Implementation Status” section of the SOT.

These are future work, not sprint-5 regressions.

5. Conclusion: Is Sprint 5 Ready to Close?

Yes.

✅ World engine substrate implemented and tested.

✅ Commands and events defined, applied, and emitting.

✅ Read-only views for ECS/runtime are in place.

✅ Public API is exposed via sim4.world.

✅ SOTs and implementation report updated with clear status + readiness notes.

✅ Tests are green.

There are no outstanding follow-ups required on the world layer before starting Sprint 6 — Runtime Tick Pipeline.