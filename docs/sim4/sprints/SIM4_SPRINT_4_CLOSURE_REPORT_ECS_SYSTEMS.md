Sprint 4 — Systems Skeleton & Scheduler

Sprint Closure Report — sim4 / ECS

1. Sprint Summary

Goal

Implement system interfaces and register them in a deterministic scheduler, without full logic — just stable scaffolding and wiring.

We achieved the sprint goal:

All Phase B–E systems are implemented as skeletons with correct signatures and query patterns.

A canonical scheduler order is defined and tested end-to-end.

Systems are layer-pure, Rust-portable in shape, and ready for future logic sprints.

All tests (unit + integration) pass under pytest.

2. Scope & Deliverables
   2.1. Core Systems Base

Files

ecs/systems/base.py

backend/sim4/tests/systems/test_systems_base.py

Delivered

SimulationRNG

Deterministic RNG wrapper around random.Random.

Seedable, pure interface; supports at least:

random()

uniform(a, b)

Designed to be swappable with a more advanced RNG later while keeping the interface stable.

WorldViewsHandle (Protocol stub)

Minimal Protocol (or equivalent) representing read-only world views exposed to systems.

No concrete logic yet; implementations will live in world/runtime layer.

Test-only dummy implementation used to validate SystemContext wiring.

Keeps systems decoupled from any concrete world representation.

SystemContext

@dataclass
class SystemContext:
world: ECSWorld
dt: float
rng: SimulationRNG
views: WorldViewsHandle
commands: "ECSCommandBuffer"
tick_index: int


Canonical context object passed to all systems.

Aligns with SOT-SIM4-ECS-SYSTEMS.

Provides a single structured entry point for all dependencies: world, time step, randomness, views, and command channel.

ECSCommandBuffer (reused from Sprint 2)

Re-exported and used in SystemContext.

Maintains monotonically increasing seq for ECSCommands.

API includes:

commands (defensive copy)

set_component

set_field

add_component

remove_component

create_entity

destroy_entity

Sequencing behavior is tested and confirmed.

Tests

test_systems_base.py:

Confirms RNG determinism for fixed seed.

Confirms SystemContext can be instantiated with dummy world and views.

Confirms ECSCommandBuffer seq increments correctly and commands returns a defensive copy.

2.2. Phase B & C Systems (Perception & Cognition Skeletons)

Files

ecs/systems/perception_system.py

ecs/systems/cognitive_preprocessor.py

ecs/systems/emotion_gradient_system.py

ecs/systems/drive_update_system.py

ecs/systems/motive_formation_system.py

ecs/systems/plan_resolution_system.py

ecs/systems/social_update_system.py

backend/sim4/tests/systems/test_phase_bc_systems_skeleton.py

Delivered

Each system:

Defines run(self, ctx: SystemContext) -> None.

Imports substrate components per SOT (e.g. Transform, RoomPresence, PerceptionSubstrate, BeliefGraphSubstrate, DriveState, MotiveSubstrate, SocialSubstrate, EmotionFields, etc.).

Declares a QuerySignature with appropriate read/write sets.

Calls ctx.world.query(signature) and iterates over results.

Performs no ECS mutations (no commands enqueued; loop is a no-op beyond possibly touching row.entity).

Systems included:

PerceptionSystem (Phase B)

CognitivePreprocessor

EmotionGradientSystem

DriveUpdateSystem

MotiveFormationSystem

PlanResolutionSystem

SocialUpdateSystem

All are logic-free scaffolds: ready to host real behavior in later sprints.

Tests

test_phase_bc_systems_skeleton.py:

Builds minimal ECSWorld with a few substrate components.

Creates seeded SimulationRNG, dummy WorldViewsHandle, and ECSCommandBuffer.

Instantiates each Phase B/C system.

Calls run(ctx) and asserts no exceptions (even if queries return 0 rows).

2.3. Phase D & E Systems (Intention & Action Skeletons)

Files

ecs/systems/intent_resolver_system.py

ecs/systems/movement_resolution_system.py

ecs/systems/interaction_resolution_system.py

ecs/systems/inventory_system.py

ecs/systems/action_execution_system.py

backend/sim4/tests/systems/test_phase_de_systems_skeleton.py

Delivered

Each system:

Implements run(self, ctx: SystemContext) -> None.

Uses QuerySignature to read/write appropriate component bundles, matching SOT-SIM4-ECS-SYSTEMS.

Iterates query results with a no-op loop; no commands emitted.

Systems included:

Phase D

IntentResolverSystem

Reads: PrimitiveIntent, MotiveSubstrate, PlanLayerSubstrate, DriveState, Transform, RoomPresence.

Writes: SanitizedIntent.

MovementResolutionSystem

Reads: SanitizedIntent, Transform, RoomPresence, PathState, MovementIntent, ActionState (plus optional traits).

Writes: MovementIntent, PathState, ActionState.

InteractionResolutionSystem

Reads: SanitizedIntent, Transform, RoomPresence, InventorySubstrate, ItemState, ActionState, InteractionIntent.

Writes: InteractionIntent, ActionState.

InventorySystem

Reads/Writes: InventorySubstrate, ItemState, InteractionIntent, ActionState.

Phase E

ActionExecutionSystem

Reads: MovementIntent, PathState, InteractionIntent, ActionState, Transform, RoomPresence, InventorySubstrate, ItemState.

Writes: Transform, RoomPresence, PathState, ActionState, InventorySubstrate, ItemState.

Intended later to emit world commands; currently no-op.

Tests

test_phase_de_systems_skeleton.py:

Constructs minimal ECSWorld with just enough structure to satisfy signatures (empty results allowed).

Creates SystemContext as in Phase B/C tests.

Runs all Phase D & E systems.

Asserts that no system raises.

2.4. Scheduler Order & Integration

Files

ecs/systems/scheduler_order.py

backend/sim4/tests/systems/test_scheduler_order.py

backend/sim4/tests/systems/test_systems_integration_skeleton.py

Delivered

Canonical Scheduler Registry

from ecs.systems.perception_system import PerceptionSystem
from ecs.systems.cognitive_preprocessor import CognitivePreprocessor
from ecs.systems.emotion_gradient_system import EmotionGradientSystem
from ecs.systems.drive_update_system import DriveUpdateSystem
from ecs.systems.motive_formation_system import MotiveFormationSystem
from ecs.systems.plan_resolution_system import PlanResolutionSystem
from ecs.systems.social_update_system import SocialUpdateSystem
from ecs.systems.intent_resolver_system import IntentResolverSystem
from ecs.systems.movement_resolution_system import MovementResolutionSystem
from ecs.systems.interaction_resolution_system import InteractionResolutionSystem
from ecs.systems.inventory_system import InventorySystem
from ecs.systems.action_execution_system import ActionExecutionSystem

PHASE_B_SYSTEMS = [PerceptionSystem]
PHASE_C_SYSTEMS = [
CognitivePreprocessor,
EmotionGradientSystem,
DriveUpdateSystem,
MotiveFormationSystem,
PlanResolutionSystem,
SocialUpdateSystem,
]
PHASE_D_SYSTEMS = [
IntentResolverSystem,
MovementResolutionSystem,
InteractionResolutionSystem,
InventorySystem,
]
PHASE_E_SYSTEMS = [ActionExecutionSystem]


Lists contain classes, not instances, so runtime can choose lifetime strategy (per-tick or long-lived instances).

Order matches SOT-SIM4-ECS-SYSTEMS.

Scheduler Smoke Test

test_scheduler_order.py:

Verifies that each PHASE_*_SYSTEMS element is a callable class.

Instantiates each system and calls run(ctx) with a dummy SystemContext.

Confirms no errors for a “null” world.

Full Integration Smoke Test

test_systems_integration_skeleton.py:

Builds a shared ECSWorld.

Constructs SystemContext with:

Seeded SimulationRNG.

DummyWorldViews.

Fresh ECSCommandBuffer.

tick_index varying across ticks.

For multiple ticks:

Runs all phases in canonical order: B → C → D → E.

Confirms:

No exceptions raised.

No commands enqueued by skeleton systems (buffer remains empty).

RNG is usable and deterministic (light sanity check).

3. Definition of Done Check

Sprint DoD

✅ All targeted files exist and compile:

base.py, all systems modules, scheduler_order.py.

✅ Each system:

Accepts SystemContext.

Declares at least one QuerySignature.

Iterates query results.

Does not implement complex logic or emit commands.

✅ SystemContext, WorldViewsHandle, SimulationRNG, and ECSCommandBuffer are available from ecs/systems/base.py.

✅ Scheduler registry exposes PHASE_B_SYSTEMS, PHASE_C_SYSTEMS, PHASE_D_SYSTEMS, PHASE_E_SYSTEMS with correct classes and order.

✅ Tests:

Unit tests for base types and each phase’s skeleton systems.

Scheduler smoke tests.

A combined integration test (test_systems_integration_skeleton.py) running all B–E systems together.

All tests pass via pytest.

Conclusion: Sprint 4 is complete and meets the agreed Definition of Done.

4. Architectural Alignment & Constraints

Rust Portability (Shapes Only)

All systems are thin Python scaffolds over ECS queries.

Types and patterns are chosen to mirror shapes that can be ported to Rust later (system structs with run(ctx)-style methods).

Layer Purity

Systems depend only on:

ECS types (ECSWorld, substrates, query signatures).

SystemContext components (rng, views, commands).

No imports from narrative or rendering layers.

Determinism & Reproducibility

RNG is seedable and scoped via SystemContext.

Scheduler order is canonical and explicitly tested.

5. Known Limitations (Intentional for This Sprint)

These are not bugs but explicit constraints of Sprint 4:

No real behavior:

Systems do not yet:

Modify components.

Enqueue ECS commands.

Use WorldViews meaningfully.

WorldViewsHandle is still a stub:

Only structural existence and type compatibility are guaranteed.

These items are expected to be addressed in later sprints (e.g., Sprint 5+).

6. Recommendations & Next Steps

For upcoming sprints:

WorldViews Implementation

Flesh out WorldViewsHandle with:

Room/graph queries (agents in room, neighbors, etc.).

Social/relationship lookups.

Implement a concrete runtime-backed WorldViews fulfilling the protocol.

System Logic Incrementalization

Turn on behavior one layer at a time:

Start with Perception → Belief → Drives (B + early C).

Then Motive formation + Plan resolution.

Finally Intent + Action.

Command Buffer Usage

Introduce controlled usage of ECSCommandBuffer in one or two systems as a prototype:

E.g., simple movement or state change.

Add tests verifying:

Command ordering per tick.

Idempotent handling.

More Sophisticated Integration Tests

Once minimal logic is added:

Introduce micro-scenarios (“1 agent, 2 rooms, 1 door”).

Validate that running B→E changes world state as expected.

7. One-Line Closure

Sprint 4 delivered a complete, deterministic skeleton for the sim4 systems stack and scheduler — all systems exist, all phases run in order, and the pipeline is now ready for real behavior to be layered in during subsequent sprints.