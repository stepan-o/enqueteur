Sprint 2 — Closure Report
Theme: ECS Commands, Command Application, and Tick-Path Sanity Check

1. Sprint Overview

Sprint goal:
Turn the ECS layer from “direct mutators only” into a command-driven substrate that:

Uses a canonical ECSCommand shape (Rust-portable).

Applies mutations deterministically via ECSWorld.apply_commands.

Gives systems a safe way to build commands (ECSCommandBuffer).

Proves the full path via end-to-end, tick-style tests.

This sprint covered the “Phase E core” of the runtime DAG from the perspective of ECS.

2. Sub-Sprint Summary
   2.1 — ECSCommand & ECSCommandKind

Files:

backend/sim4/ecs/commands.py

backend/sim4/tests/test_ecs_commands.py

What was implemented:

ECSCommandKind(str, Enum) with stable string values:

class ECSCommandKind(str, Enum):
SET_FIELD = "set_field"
SET_COMPONENT = "set_component"
ADD_COMPONENT = "add_component"
REMOVE_COMPONENT = "remove_component"
CREATE_ENTITY = "create_entity"
DESTROY_ENTITY = "destroy_entity"


These string values are now part of the cross-language contract for Python ↔ Rust.

ECSCommand dataclass:

@dataclass(frozen=True)
class ECSCommand:
seq: int
kind: ECSCommandKind

    entity_id: Optional[EntityID] = None
    component_type: Optional[type] = None
    component_instance: Optional[object] = None
    field_name: Optional[str] = None
    field_value: Optional[object] = None


Helper constructors (for systems & tests):

cmd_set_field

cmd_set_component

cmd_add_component

cmd_remove_component

cmd_create_entity (uses component_instance to carry list[object] | None)

cmd_destroy_entity

Key decisions:

seq is explicitly part of the type (deterministic ordering).

Enum values are stable strings, not ints, making logs and cross-language mapping easier.

For Sprint 2 only, CREATE_ENTITY reuses component_instance as an “optional list payload” for initial components. This is documented as an interim compromise.

2.2 — ECSWorld.apply_commands (SET_COMPONENT, SET_FIELD)

Files:

backend/sim4/ecs/world.py

backend/sim4/tests/test_ecs_world_apply_commands_basic.py

What was implemented:

Added apply_commands(self, commands: Iterable[ECSCommand]) -> None to ECSWorld:

Commands are sorted by seq:

sorted_cmds = sorted(commands, key=lambda c: c.seq)


Dispatcher supports:

ECSCommandKind.SET_COMPONENT

ECSCommandKind.SET_FIELD

(Others temporarily raise NotImplementedError at this stage; later filled in during 2.3.)

SET_COMPONENT semantics:

Requires entity_id and component_instance.

Fail-fast if entity does not exist (raises ValueError).

Delegates to add_component, which:

Replaces existing component instance if type is present.

Otherwise, adds the component, moving entity to appropriate archetype.

SET_FIELD semantics:

Requires entity_id, component_type, field_name.

Fail-fast in all invalid cases:

Entity missing → ValueError.

Component missing → ValueError.

Field missing on component → AttributeError.

Uses setattr for a simple, Rust-portable “struct field write” analog.

Result:
We now have a deterministic, fail-fast mutation path for updates that don’t change archetypes.

2.3 — Entity Lifecycle + Add/Remove Component

Files:

backend/sim4/ecs/world.py (extended dispatcher)

backend/sim4/tests/test_ecs_world_apply_commands_full.py

New dispatcher cases:

CREATE_ENTITY → _apply_create_entity

DESTROY_ENTITY → _apply_destroy_entity

ADD_COMPONENT → _apply_add_component

REMOVE_COMPONENT → _apply_remove_component

Semantics:

CREATE_ENTITY

Ignores entity_id (IDs come from EntityAllocator).

Treats cmd.component_instance as None | list[object].

None → no initial components.

list[object] → initial component instances.

Uses world.create_entity() then add_component for each component.

Raises ValueError if payload is something other than None or list.

DESTROY_ENTITY

Requires entity_id.

If entity missing → deterministic no-op (no exception).

Calls world.destroy_entity, which:

Uses swap-remove on archetype storage.

Keeps _entities mapping consistent.

Notifies allocator (for potential future reuse).

ADD_COMPONENT

Requires entity_id and component_instance.

Fail-fast if entity missing (ValueError).

Uses get_component to check existence:

If absent → add_component (archetype move).

If present → overwrite via add_component (idempotent “upsert” semantics).

REMOVE_COMPONENT

Requires entity_id and component_type.

Fail-fast if entity missing.

Deterministic no-op if entity lacks that component.

Uses remove_component to move entity to new archetype without that component.

Additional helper:

has_entity(self, entity_id: EntityID) -> bool

iter_entity_ids(self) -> Iterable[EntityID] (sorted ascending; deterministic; used in tests).

Result:
All core ECS mutations required by systems can now be expressed as ECSCommands and applied via apply_commands.

2.4 — ECSCommandBuffer

Files:

backend/sim4/ecs/systems/base.py

backend/sim4/ecs/systems/__init__.py

backend/sim4/tests/test_ecs_command_buffer.py

What was implemented:

@dataclass
class ECSCommandBuffer:
_next_seq: int = 0
_commands: List[ECSCommand] = field(default_factory=list)

    @property
    def commands(self) -> List[ECSCommand]:
        return list(self._commands)

    def set_component(self, entity_id, component_instance) -> None: ...
    def set_field(self, entity_id, component_type, field_name: str, value) -> None: ...
    def add_component(self, entity_id, component_instance) -> None: ...
    def remove_component(self, entity_id, component_type) -> None: ...
    def create_entity(self, components: Optional[List[object]] | None = None) -> None: ...
    def destroy_entity(self, entity_id) -> None: ...


All methods:

Use _next_seq as the seq for the command, then increment.

Build commands via the helper constructors from ecs.commands.

Append to _commands.

Invariants enforced by tests:

Within one buffer:

commands[i].seq == i (monotonic, gapless).

Strictly increasing seq over the call sequence.

.commands returns a defensive copy; mutating the returned list does not affect the buffer.

Each method produces the correct ECSCommandKind and sets the expected fields (entity_id, component_type, etc.).

Result:
Systems now have a deterministic, Rust-portable way to build command sequences without thinking about seq or low-level command wiring.

2.5 — End-to-End Tick Simulation Tests

File:

backend/sim4/tests/test_ecs_tick_simulation.py

Goal:
Prove the intended production path:

systems → ECSCommandBuffer → ECSWorld.apply_commands → ECS state

…works correctly and deterministically.

Key elements:

Simple component:

@dataclass
class Health:
value: int

Test 1 — Healing Tick

Setup:

world = ECSWorld()

e = world.create_entity(initial_components=[Health(value=10)])

“System logic” in test:

buf = ECSCommandBuffer()
buf.set_field(entity_id=e, component_type=Health, field_name="value", value=15)
world.apply_commands(buf.commands)


Assert: Health.value == 15.

This validates SET_FIELD + buffer integration end-to-end.

Test 2 — Spawn & Modify

First “tick”:

Use ECSCommandBuffer.create_entity twice with different Health values (1, 10).

Apply commands; entities are created via CREATE_ENTITY.

Query world for Health:

results = world.query((Health,)).to_list()
assert len(results) == 2
entity_ids = [eid for eid, (_h,) in results]


Second “tick”:

Use a new buffer to set_field:

Lowest ID → value = 2

Highest ID → value = 20

Re-query and assert:

There are still exactly 2 entities.

They are returned sorted by entity ID.

Final Health values are {2, 20} with correct entity ordering.

This tests:

CREATE_ENTITY path via commands.

Query order determinism.

SET_FIELD after entities are created via commands.

Determinism Scenario

_run_tick_scenario_snapshot():

Sets up a fresh world with two entities created via create_entity (direct API; allowed for setup).

Uses buffer to:

Update both Health values.

Create a new entity with Health(value=1).

Applies commands.

Builds snapshot: [(entity_id, health_value), ...], sorted by entity_id.

test_tick_scenario_is_deterministic:

Calls the scenario twice and asserts snapshots are identical.

Result:
We now have tests that walk the entire intended Sim4 tick path for ECS. No direct mutators are used inside the “system path” itself, only for initial setup.

3. SOT Alignment
   ECS Core (SOT-SIM4-ECS-CORE)

Implemented & aligned:

ECSWorld.apply_commands as the sole mutation point in tick semantics.

Deterministic ordering via seq sort.

Rust-portable types (int IDs, dataclasses, lists, dicts).

Fail-fast semantics for invalid commands vs. deterministic no-ops for idempotent cases (destroying missing entity, removing absent component).

Clarified in SOT prompt (ready to patch):

Updated ECSCommand shape to include:

seq

ECSCommandKind(str, Enum) with exact string values.

entity_id, component_type, component_instance, field_name, field_value.

Documented the Sprint 2 CREATE_ENTITY payload compromise (component_instance as list[object] | None).

Clarified that runtime uses apply_commands in Phase E, while direct ECSWorld methods are reserved for setup/tests.

ECS Systems (SOT-SIM4-ECS-SYSTEMS)

Implemented & aligned:

ECSCommandBuffer in ecs/systems/base.py with monotonic seq and convenience methods.

Clarified in SOT prompt:

ECSCommandBuffer signature aligned to:

create_entity(self, components: list[object] | None = None)

no archetype_code parameter (archetypes inferred from component types).

.commands returns a defensive copy.

Systems never call mutating methods on ECSWorld directly; they always go through ECSCommandBuffer → ECSWorld.apply_commands.

4. Quality & Testing

New test suites:

test_ecs_commands.py

Validates enum values, helper constructors, and field wiring.

test_ecs_world_apply_commands_basic.py

SET_COMPONENT / SET_FIELD, replacement behavior, and seq-ordering.

test_ecs_world_apply_commands_full.py

Full lifecycle: CREATE, ADD, SET_FIELD, DESTROY, archetype moves, and determinism.

test_ecs_command_buffer.py

Monotonic seq, correct kinds, payload wiring, defensive .commands.

test_ecs_tick_simulation.py

End-to-end mini tick scenarios, including determinism checks.

All tests pass locally.

5. Known Gaps / Technical Debt

World commands from systems (emit_world_command)

Defined conceptually in SOT-SYSTEMS, but not yet implemented in ECSCommandBuffer.

For now, we are focusing purely on ECS mutations.

Separation of “payload” vs components for CREATE_ENTITY

Current compromise overloads component_instance with a list.

For SimX/Rust we’ll likely want an explicit components: list field or a specific CreateEntityPayload.

Runtime enforcement

The architecture intent is that only Phase E mutates ECS via apply_commands.

Right now, this is enforced by convention + tests; runtime adapters still need to be wired to obey this strictly.

Full systems set

This sprint focused on the ECS substrate (commands + world).

The actual systems (perception, emotion, drives, motives, plans, etc.) are still to be implemented, but the path they will use is now defined and tested.

6. Recommendations for Sprint 3

Proposed themes:

Runtime Tick Integration (Phase B–E plumbing)

Implement SystemContext, WorldViewsHandle, and a minimal scheduler_order.py.

Wire runtime to:

Create an ECSCommandBuffer per tick.

Run systems in Phase B–D.

Call world.apply_commands(buffer.commands) in Phase E.

Minimal System Set (Happy-path)

Implement one or two simple substrate systems (e.g., PerceptionSystem + a tiny “Health regen” or “Drive decay” system) that use queries + ECSCommandBuffer.

Extend the current tick tests to use real system classes (not ad-hoc “system logic in tests”).

SOT & Doc Sync

Apply the SOT patches specified in the previous prompt (if not already done).

Add short “Implementation Notes” sections to SOTs to distinguish Sim4 prototype compromises from SimX target design.

Debug & Introspection

Add debug helpers:

Simple ECS snapshot view for tests.

Optional logging adapter that can be toggled to inspect ECSCommand streams.

7. Sprint 2 Summary in One Paragraph

Sprint 2 successfully moved the Sim4 ECS substrate to a command-driven, deterministic mutation model. We now have a canonical ECSCommand type with stable, Rust-portable enums; an ECSWorld.apply_commands that handles full entity lifecycle and component mutations solely through commands; an ECSCommandBuffer that systems can use without touching seq or mutators directly; and end-to-end tests that validate the intended “systems → buffer → apply_commands” tick path and its determinism. The remaining work is mostly about connecting this clean substrate to the runtime tick and systems, plus polishing SOT docs and a few payload-shape compromises for future Rust alignment.