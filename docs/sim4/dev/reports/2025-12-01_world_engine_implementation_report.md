Sim4 World Engine Implementation Report — Sprint 5 (5.1–5.5)

Author: Junie (Sim4 implementation assistant)
Date: 2025-12-01 14:46 (local)

Purpose
- Provide a concise, implementation-focused report for the Sim4 world engine (world/), readying it for Sprint 6 runtime tick wiring.
- Summarize what exists (data structures, commands/events, applier, views), how it aligns with SOTs, and what remains TODO.

Layer Position & Constraints (SOP-100/200)
- DAG: runtime → ecs → world → snapshot → integration; narrative is a sidecar reader.
- Layer purity: world/ does not import from ecs/, runtime/, snapshot/, narrative/, or integration/.
- Determinism: data structures are Rust-portable (ints, bools, lists/dicts/sets, frozensets, dataclasses). No time or I/O. World commands are applied in seq order.

Public API Surface (world/__init__.py)
from sim4.world import (
  WorldContext, RoomRecord, ItemRecord,
  WorldCommand, WorldCommandKind,
  WorldEvent, WorldEventKind,
  apply_world_commands,
  WorldViews, RoomView,
)

Core Data Structures (backend/sim4/world/context.py)
- Local ID aliases: RoomID = int, AgentID = int, ItemID = int, DoorID = int.
- Records:
  - RoomRecord(id: RoomID, label: Optional[str]) — frozen.
  - ItemRecord(id: ItemID, room_id: Optional[RoomID]) — mutable room_id.
- WorldContext (mutable):
  - rooms_by_id: dict[RoomID, RoomRecord]
  - agent_room: dict[AgentID, RoomID]
  - room_agents: dict[RoomID, set[AgentID]]
  - items_by_id: dict[ItemID, ItemRecord]
  - room_items: dict[RoomID, set[ItemID]]
  - door_open: dict[DoorID, bool]
- Helpers (explicit error semantics; deterministic):
  - register_room(room), get_room(room_id)
  - register_agent(agent_id, room_id), move_agent(agent_id, new_room_id), get_agent_room(agent_id), get_room_agents(room_id)
  - register_item(item), move_item(item_id, new_room_id | None), get_room_items(room_id)
  - register_door(door_id, is_open=False), set_door_open(door_id, open), is_door_open(door_id)
  - Convenience: apply_world_commands(commands), make_views()

World Commands & Events (backend/sim4/world/commands.py, events.py)
- WorldCommandKind (string-backed; SOT-aligned):
  - "set_agent_room", "spawn_item", "despawn_item", "open_door", "close_door"
- WorldEventKind (string-backed; SOT-aligned):
  - "agent_moved_room", "item_spawned", "item_despawned", "door_opened", "door_closed"
- WorldCommand (frozen dataclass):
  - seq: int; kind: WorldCommandKind
  - agent_id: int | None; room_id: int | None; item_id: int | None; door_id: int | None
  - state_code: int | None; flag: int | None (reserved payloads)
- WorldEvent (frozen dataclass):
  - kind: WorldEventKind
  - agent_id: int | None; room_id: int | None; previous_room_id: int | None; item_id: int | None; door_id: int | None
- Helper constructors:
  - make_set_agent_room(seq, agent_id, room_id), make_spawn_item(seq, item_id, room_id),
    make_despawn_item(seq, item_id), make_open_door(seq, door_id), make_close_door(seq, door_id)

Deterministic Command Application (backend/sim4/world/apply_world_commands.py)
- apply_world_commands(world_ctx, commands: Iterable[WorldCommand]) -> List[WorldEvent]
  - Converts iterable to list; sorts by cmd.seq ascending (stable).
  - Mutates WorldContext via public helpers only; propagates errors (ValueError/KeyError).
  - Emits WorldEvent instances for successful mutations; no events on failure.
  - Raises NotImplementedError for unknown command kinds.
- Implemented handlers:
  - SET_AGENT_ROOM → move_agent → AGENT_MOVED_ROOM(agent_id, previous_room_id, room_id)
  - SPAWN_ITEM → register_item → ITEM_SPAWNED(item_id, room_id)
  - OPEN_DOOR → set_door_open(True) → DOOR_OPENED(door_id)
  - Additionally: CLOSE_DOOR → DOOR_CLOSED; DESPAWN_ITEM → move_item(None) → ITEM_DESPAWNED

Read‑only Views (backend/sim4/world/views.py)
- WorldViews façade over WorldContext (read-only; immutable return types):
  - get_agent_room(agent_id) -> Optional[RoomID]
  - get_room_agents(room_id) -> FrozenSet[AgentID]
  - get_room_items(room_id) -> FrozenSet[ItemID]
  - is_door_open(door_id) -> bool
  - get_room_view(room_id) -> RoomView(room_id, agents: FrozenSet, items: FrozenSet)
  - iter_room_neighbors(room_id) -> Iterable[RoomID] — returns () as a safe stub (TODO[NAVGRAPH])
- Guarantees:
  - No mutation APIs; no live mutable references; frozenset/tuple return types.

Spec Alignment (SOT-SIM4-WORLD-ENGINE, SOT-SIM4-ECS-COMMANDS-AND-EVENTS)
- Names and enum string constants exactly match the SOTs.
- Command/event dataclass fields match the documented shapes.
- Deterministic apply ordering by seq is implemented; error propagation and NotImplementedError semantics are respected.
- Layer purity upheld; all data types are Rust-portable.

Known Gaps / TODO[WORLD]
- NavGraph/neighbor topology: iter_room_neighbors is a stub returning ().
- Snapshot/episode integration not yet wired to consume WorldEvents.
- Runtime tick wiring (construction/injection of views, world command bus) is deferred to Sprint 6.

Ready for Sprint 6 (Runtime Tick)
- Runtime can rely on:
  - World public API via sim4.world, stable command/event kinds, deterministic applier, read‑only views.
  - Explicit error semantics; immutable query results.
- Runtime must supply:
  - Construction of WorldContext and WorldViews; sequencing and dispatch of WorldCommand batches; event routing to history/snapshot.
- Not ready:
  - Neighbor graph; any semantics depending on nav/visibility topology.

Test Coverage (backend/sim4/tests/world)
- test_world_context.py — room/agent/item registration & movement; immutability; invalid cases.
- test_world_commands_events.py — command/event construction, enum value stability, immutability.
- test_apply_world_commands.py — applier behavior (ordering, events, error propagation, unhandled kinds).
- test_world_views.py — views reflect state post-commands, immutability, no aliasing, error behavior.

Appendix — Quick Reference
- Apply commands deterministically:
  from sim4.world import apply_world_commands
  events = apply_world_commands(world_ctx, cmds)

- Construct views for systems (runtime will inject):
  from sim4.world import WorldViews
  views = WorldViews(world_ctx)

- Command helpers:
  from sim4.world import make_set_agent_room, make_spawn_item, make_open_door
  cmds = [
    make_spawn_item(seq=1, item_id=10, room_id=2),
    make_set_agent_room(seq=2, agent_id=100, room_id=2),
    make_open_door(seq=3, door_id=7),
  ]
