Sim4 ECS Implementation Overview — Core, Components, Systems, and Connections

Author: Junie (Sim4 implementation assistant)
Date: 2025-12-01 11:33 (local)

Purpose
- Provide a clear, implementation-focused overview of the current ECS in Sim4:
  - What files and types exist (core, components, systems)
  - How they connect within ECS (queries, commands, storage)
  - What external connections exist to other layers (runtime, world, snapshot, narrative)
  - Determinism and layer purity considerations

Scope of Code Reviewed (selected, non-exhaustive)
- Core:
  - backend/sim4/ecs/world.py (ECSWorld, queries, apply_commands)
  - backend/sim4/ecs/commands.py (ECSCommand, ECSCommandKind, helpers)
  - backend/sim4/ecs/entity.py (EntityID, EntityAllocator)
  - backend/sim4/ecs/archetype.py, backend/sim4/ecs/storage.py, backend/sim4/ecs/query.py (archetype + storage + query engine)
- Systems:
  - backend/sim4/ecs/systems/base.py (SystemContext, SimulationRNG, ECSCommandBuffer, WorldViewsHandle Protocol)
  - Representative systems: perception_system.py, cognitive_preprocessor.py, action_execution_system.py, drive_update_system.py (skeletons)
- Components:
  - backend/sim4/ecs/components/* (embodiment.py, perception.py, social.py, narrative_state.py, and others referenced by systems)

Changelog (since previous version)
- Sprint 4.5a: Introduced QuerySignature, RowView, QueryResult; all call sites migrated to the new API; deterministic ordering documented.
- Sprint 4.5b: Aligned all system QuerySignature read/write sets with SOT-SIM4-ECS-SYSTEMS; systems remain no-op skeletons.
- Sprint 4.5c: Implemented optional and without semantics in ECSWorld.query; added focused engine tests; preserved deterministic ordering.

1) ECS Core Implementation

1.1 ECSWorld (ecs/world.py)
- Responsibilities:
  - Tracks entities and component instances via an archetype-like storage backend.
  - Exposes deterministic query API: world.query(QuerySignature) → QueryResult (iterable of RowView), where each RowView provides:
    - entity: EntityID
    - components: positional tuple in canonical order: (read) + (write) + (optional). Optional component slots are None when absent.
  - Applies mutation commands with apply_commands(commands: Iterable[ECSCommand]) enforcing seq-based deterministic ordering.
- Determinism:
  - apply_commands sorts incoming commands by cmd.seq before dispatch.
  - Strict validation in _apply_set_field (entity existence, component presence, attribute existence) to fail fast.
- Supported command kinds (as of current sprint):
  - SET_COMPONENT, SET_FIELD, CREATE_ENTITY, DESTROY_ENTITY, ADD_COMPONENT, REMOVE_COMPONENT.
- CREATE_ENTITY semantics:
  - Treats ECSCommand.component_instance field as an optional payload of List[object] (interim approach); allocates a new EntityID via allocator and attaches components deterministically.
- Helper APIs:
  - has_entity(entity_id) → bool
  - add_component(entity_id, component_instance) / get_component(entity_id, component_type) (defined elsewhere in file)
  - Internal helpers (_apply_set_component, _apply_set_field, _apply_create_entity, _apply_destroy_entity, _apply_add_component, _apply_remove_component)

1.2 Entity & Storage (ecs/entity.py, ecs/storage.py, ecs/archetype.py, ecs/query.py)
- EntityID:
  - Opaque integer type (Rust-portable). Comparable/sortable for stable ordering.
- EntityAllocator:
  - Monotonic ID allocation within an episode; tracks liveness (no reuse without explicit destroy) per SOT.
- Archetype/Storage:
  - Columnar/SOA-like storage grouped by component-type signatures (ArchetypeSignature). Details are encapsulated within storage.py and archetype.py and surfaced via world.py.
- Query Engine (ecs/query.py):
  - Canonical types introduced in Sprint 4.5a:
    - QuerySignature(read: Tuple[type, ...], write: Tuple[type, ...], optional: Tuple[type, ...] = (), without: Tuple[type, ...] = ())
    - RowView(entity: EntityID, components: Tuple[object, ...]) — components layout is (read) + (write) + (optional) in the order specified by the signature; optional component positions are None if the entity lacks that component.
    - QueryResult — a deterministic iterable over RowView instances.
  - Semantics (Sprint 4.5c):
    - read/write: required; entities must have all listed types.
    - without: exclusion; entities possessing any of these types are filtered out.
    - optional: tolerated; rows include fixed-position slots (possibly None) for these types.
  - Ordering: results are deterministically ordered (currently ascending EntityID).

1.3 Commands (ecs/commands.py)
- ECSCommandKind: stable string enum values for cross-language compatibility:
  - set_field, set_component, add_component, remove_component, create_entity, destroy_entity
- ECSCommand (frozen dataclass):
  - Fields: seq (int), kind (ECSCommandKind), and optional entity_id, component_type, component_instance, field_name, field_value.
- Helper constructors:
  - cmd_set_field, cmd_set_component, cmd_add_component, cmd_remove_component, cmd_create_entity, cmd_destroy_entity
  - Note: cmd_create_entity places the components list payload in component_instance; ECSWorld consumes it in _apply_create_entity.

2) Components (ecs/components/*)

2.1 General Principles
- All components are Python dataclasses with fields restricted to Rust-portable primitives: ints, floats, bools, lists, dicts, tuples of numbers; references via EntityID or other numeric aliases (e.g., RoomID). No free-text narrative fields.
- Systems enforce interpretation and ranges; components remain passive storage only.

2.2 Selected Component Modules
- embodiment.py:
  - Aliases: RoomID = int, AssetID = int.
  - Transform(room_id: RoomID, x: float, y: float, orientation: float)
  - Velocity(dx: float, dy: float)
  - RoomPresence(room_id: RoomID, time_in_room: float)
  - PathState(active: bool, waypoints: List[Tuple[float, float]], current_index: int, progress_along_segment: float, path_valid: bool)
- perception.py:
  - PerceptionSubstrate(visible_agents: List[EntityID], visible_assets: List[AssetID], visible_rooms: List[RoomID], proximity_scores: Dict[EntityID, float])
  - AttentionSlots(focused_agent: Optional[EntityID], focused_asset: Optional[AssetID], focused_room: Optional[RoomID], secondary_targets: List[EntityID], distraction_level: float)
  - SalienceState(agent_salience: Dict[EntityID, float], topic_salience: Dict[int, float], location_salience: Dict[RoomID, float])
- social.py:
  - SocialSubstrate(relationship_to, trust_to, respect_to, resentment_to: Dict[EntityID, float])
  - SocialImpressionState(impression_code_to: Dict[EntityID, int], misunderstanding_level_to: Dict[EntityID, float])
  - FactionAffinityState(faction_affinity: Dict[int, float], faction_loyalty: Dict[int, float])
- narrative_state.py:
  - NarrativeState(narrative_id: int, last_reflection_tick: int, cached_summary_ref: Optional[int], tokens_used_recently: int)
  - Explicitly marked as narrative-owned; ECS systems must treat as read-only.
- Additional referenced modules (present and used by systems/tests): identity.py, drives.py, emotion.py, motive_plan.py, inventory.py, intent_action.py, belief.py.

3) Systems (ecs/systems/*)

3.1 Base Infrastructure (ecs/systems/base.py)
- SimulationRNG(seed: int): deterministic RNG wrapper exposing .random() and .uniform(a, b).
- WorldViewsHandle (Protocol): placeholder for read-only views of the world layer; concrete impls live in world/runtime.
- SystemContext:
  - Fields: world (ECSWorld), dt (float), rng (SimulationRNG), views (WorldViewsHandle), commands (ECSCommandBuffer), tick_index (int).
  - Convention: world is treated as read-only; systems issue mutations via commands buffer.
- ECSCommandBuffer:
  - Monotonic per-buffer sequence assignment (seq starts at 0).
  - Methods: set_component, set_field, add_component, remove_component, create_entity(components: Optional[List[object]] = None), destroy_entity.
  - commands property returns a defensive copy for safety/determinism.

3.2 Representative System Skeletons
- PerceptionSystem (perception_system.py):
  - Query: QuerySignature(read=(Transform, RoomPresence, ProfileTraits), write=(PerceptionSubstrate, AttentionSlots, SalienceState))
  - Behavior: iterate deterministically; no side effects yet.
- CognitivePreprocessor (cognitive_preprocessor.py):
  - Query: QuerySignature(read=(BeliefGraphSubstrate, AgentInferenceState, PerceptionSubstrate, SalienceState), write=(BeliefGraphSubstrate, AgentInferenceState))
  - Behavior: iterate deterministically; no side effects yet.
- ActionExecutionSystem (action_execution_system.py):
  - Query: QuerySignature(read=(MovementIntent, PathState, InteractionIntent, ActionState, Transform, RoomPresence, InventorySubstrate, ItemState), write=(Transform, RoomPresence, PathState, ActionState, InventorySubstrate, ItemState))
  - Behavior: iterate deterministically; placeholders for future ECS/world commands.
- DriveUpdateSystem (drive_update_system.py):
  - Query: QuerySignature(read=(DriveState, EmotionFields, MotiveSubstrate), write=(DriveState,))
  - Behavior: iterate deterministically; no side effects yet.

3.3 Scheduler and Phase Context
- Systems are grouped conceptually by phases (B–F) per SOT-SIM4-ECS-SYSTEMS, though full scheduler wiring lives in the runtime layer (not in ecs/). Current implementations are skeletons oriented to deterministic queries.

4) How Pieces Connect Inside ECS

- Systems → ECSWorld:
  - Systems construct QuerySignature with SOT-aligned read/write sets and call ctx.world.query(signature) to obtain deterministic RowView results.
  - Systems must not mutate world directly; they enqueue ECSCommand instances into ctx.commands (ECSCommandBuffer).
- ECSCommandBuffer → ECSCommand → ECSWorld.apply_commands:
  - Each buffer assigns a local, monotonically increasing seq to commands in the order they were enqueued.
  - Runtime later aggregates these commands across systems and provides a globally ordered sequence into ECSWorld.apply_commands. ECSWorld sorts by seq and dispatches to type-specific _apply_* handlers.
- Storage/Archetypes → Queries:
  - ECSWorld delegates to storage/query engine to produce deterministic iteration over matching entities; components are retrieved in a fixed order.

5) External Connections to Other Layers

- Runtime (backend/sim4/runtime):
  - Owns system scheduling and tick sequencing (per SOT-SIM4-RUNTIME-TICK).
  - Aggregates commands from ECSCommandBuffer instances across systems, assigns or maintains global seq ordering, and calls ECSWorld.apply_commands.
  - Provides seeded RNG seeds for SimulationRNG to ensure replayable determinism.
- World (backend/sim4/world):
  - Hosts WorldContext and WorldCommand/WorldEvent (per SOT-SIM4-WORLD-ENGINE and SOT-SIM4-ECS-COMMANDS-AND-EVENTS). ECS systems may propose WorldCommands during Phase F via runtime-provided buffers (not implemented in ecs/).
  - WorldViewsHandle Protocol in ecs/systems/base.py is fulfilled by a world/runtime-provided adapter that exposes read-only world information to systems.
- Snapshot (backend/sim4/snapshot):
  - Consumes emitted WorldEvents and ECS state to generate read-only snapshots. ECS does not import snapshot directly.
- Narrative (backend/sim4/narrative):
  - Interacts via DTOs and adapters; NarrativeState component serves as a numeric handle. Narrative does not directly mutate ECS; changes flow through runtime-approved mechanisms.
- Integration (backend/sim4/integration):
  - Top-level interfaces to external tooling/UX; sits above snapshot and runtime.

6) Determinism & Layer Purity

- Determinism:
  - Commands are sorted by seq before application; systems/queries iterate in a deterministic, stable order (query results currently ordered by ascending EntityID).
  - Query RowView.components uses a canonical, deterministic layout: (read) + (write) + (optional); optional slots are None when absent.
  - RNG usage is explicit via SimulationRNG with externally provided seed.
- Layer Purity:
  - ecs/ does not import runtime/, world/, snapshot/, narrative/, or integration/.
  - Systems import only ecs.world and ecs.components.* plus ecs.systems.base.
  - Cross-layer communication occurs via DTOs/protocols (SystemContext, WorldViewsHandle) provided by runtime/world.

7) Known Gaps / TODO[ARCH]

- Cross-buffer global sequencing:
  - Runtime must define and enforce how multiple ECSCommandBuffer instances are merged into a single globally ordered stream prior to applying to ECSWorld. Current ecs implementation assumes sorted by seq.
- WorldViewsHandle methods:
  - Protocol is a placeholder; need to define initial minimal read-only methods (e.g., agents_in_room(room_id), room_neighbors(room_id)) and implement in runtime/world.
- CREATE_ENTITY payload field:
  - Interim use of component_instance to carry a list payload; consider adding a dedicated payload field in a future SOT-aligned refactor.
- Read-only enforcement:
  - Python cannot enforce read-only access to ctx.world; rely on conventions, tests, or dev-time wrappers provided by runtime for guardrails.

Appendix — Quick Reference

- Issue ECS mutations from systems:
  - ctx.commands.set_component(eid, comp)
  - ctx.commands.set_field(eid, ComponentType, "field", value)
  - ctx.commands.add_component(eid, comp)
  - ctx.commands.remove_component(eid, ComponentType)
  - ctx.commands.create_entity([comp1, comp2, ...])
  - ctx.commands.destroy_entity(eid)

- Deterministic RNG usage:
  - r = ctx.rng
  - p = r.random()
  - x = r.uniform(a, b)

Conclusion
- The current ECS implementation is structured and wired according to the SOTs: a deterministic, Rust-portable numeric substrate with clean layer boundaries. Systems currently expose skeleton behavior with deterministic queries and a command buffer for future mutations. External connections are intentionally mediated through runtime/world adapters and DTOs, preserving the 6-layer DAG purity.
