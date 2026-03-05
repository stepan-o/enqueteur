# 📘 SOT-SIM4-ECS-SYSTEMS
_**Canonical deterministic systems for agent substrate evolution**_
**Draft 1.0 — Architect-Level, Rust-Aligned, SOP-100/200/300 Compliant**

---

## 0. Scope & Purpose

This SOT defines the **ECS systems** that operate over the substrate components defined in `SOT-SIM4-ECS-SUBSTRATE-COMPONENTS`, within the constraints of `SOT-SIM4-ECS-CORE` and the tick pipeline in `SOT-SIM4-RUNTIME-TICK`.

It answers:
* Which systems live under ecs/systems/.
* Which tick phase (SOP-200) each system belongs to.
* Which components and world views each system reads.
* What commands / mutations each system produces.
* How systems map to:
  * the **7-layer agent mind** (SOP-300),
  * the **Free Agent Spec** (SelfModel, DriveState, MotiveSystem, SocialMind, etc.).
* How ECS systems maintain:
  * determinism and replayability,
  * layer purity (no world/narrative imports),
  * Rust-portable logic.

This doc is the single source of truth for ECS system behavior and ordering.  
Any new or changed system must be added here and to ecs/systems/scheduler_order.py.

---

## 0.A Implementation Note — Sim4 Sprint 4 (Python Prototype)

For the Sim4 Python prototype at the end of Sprint 4:

- Systems under ecs/systems/ are implemented as skeletons that:
  - Define QuerySignature read/write sets aligned with this SOT.
  - Use SystemContext (world, rng, views, commands, dt, tick_index).
  - Iterate deterministically over queries (no side effects during iteration).
  - Do not implement full behavioral logic yet; they enqueue no ECS/world commands beyond scaffolding.
- The emphasis for Sprint 4 is interface correctness and SOT-aligned system signatures. Behavioral logic (perception, drive updates, social updates, intent resolution, action execution, etc.) will be added in subsequent sprints.

This note clarifies that the current lack of complex behavior is intentional and compliant with the milestone scope.

## 1. Global Design Rules for ECS Systems
All systems are constrained by the locked SOPs and SOTs.

1.1 Pure, Deterministic Logic

Each system is a pure function of:

current ECS state (via ECSWorld read access),

injected world views (read-only),

tick delta dt,

deterministic RNG handle (from util/random.py),

tick-local buffers (e.g. event summaries).

Systems:

do not perform I/O,

do not call LLMs or narrative,

do not read OS time or environment,

do not rely on Python’s global random or non-deterministic APIs.

Given the same initial state + seed + inputs → same outputs.

1.2 No Direct World or Narrative Access

Systems never import from:

world/

runtime/

narrative/

snapshot/

integration/

World data comes in via WorldViews objects created by runtime/world_context.py.
Narrative influence comes as PrimitiveIntent (already written into ECS prior to the tick).

1.3 Controlled Mutation via Tick Phases

Per SOT-SIM4-RUNTIME-TICK:

tick(dt):
1. Lock WorldContext
2. Update Clock
3. Phase A: Input Processing
4. Phase B: Perception
5. Phase C: Cognition (non-LLM)
6. Phase D: Intention → ECS Commands
7. Phase E: ECS Command Application (ECS mutations)
8. Phase F: World Updates
9. Phase G: Event Consolidation
10. Phase H: Diff Recording + History
11. Phase I: Narrative Trigger (post-tick)
12. Unlock WorldContext


For ECS systems:

Phase B–D systems:

read ECS state + world views,

do not directly mutate ECS storage,

instead, they write to an ECSCommandBuffer.

Phase E:

A dedicated command-application pass (runtime-side) applies the accumulated ECS commands in a stable order.

A single ActionExecutionSystem runs here in Sim4: it reads intents and path state, pushes its own ECS and world commands into the buffer, and all resulting ECS mutations are still applied via the same command-application mechanism in this phase.

All ECS state changes are thus attributable to Phase E in the tick semantics.

1.4 Substrate-Only Cognition

Systems operate purely on substrate components:

numeric / structural fields from ecs/components/*.

no natural language.

no semantic labels beyond int-coded enums.

All “meaning-making” lives in narrative/; systems see only substrate.

1.5 Stable Ordering & Rust Portability

System execution order is explicitly defined in:

ecs/systems/scheduler_order.py.

No system relies on dict/set iteration order:

always sort or iterate via EntityID order when needed.

Logic must be implementable in Rust ECS:

no reflection hacks,

no dynamic schema changes.

2. Folder Layout under ecs/systems/

Canonical Sim4 structure:

ecs/systems/
__init__.py
base.py                    # SystemContext, WorldViewsHandle, ECSCommandBuffer

perception_system.py       # PerceptionSystem
cognitive_preprocessor.py  # CognitivePreprocessor
emotion_gradient_system.py # EmotionGradientSystem
drive_update_system.py     # DriveUpdateSystem
motive_formation_system.py # MotiveFormationSystem
plan_resolution_system.py  # PlanResolutionSystem
social_update_system.py    # SocialUpdateSystem

intent_resolver_system.py        # IntentResolverSystem
movement_resolution_system.py    # MovementResolutionSystem
interaction_resolution_system.py # InteractionResolutionSystem
action_execution_system.py       # ActionExecutionSystem
inventory_system.py              # InventorySystem (optional substrate system)

scheduler_order.py         # Map systems to tick phases B–E with explicit ordering


Future Sim versions may add more modules, but they must be registered in scheduler_order.py and documented here.

3. System Interface & Context
   3.1 SystemContext (in base.py)

Shape-level concept:

@dataclass
class SystemContext:
world: ECSWorld                # read-only from system perspective
dt: float                      # delta time
rng: SimulationRNG             # deterministic RNG (substream for this system)
views: WorldViewsHandle        # read-only world adapters
commands: ECSCommandBuffer     # target for ECS & world commands
tick_index: int                # current tick index


Systems are invoked as:

class PerceptionSystem:
def run(self, ctx: SystemContext) -> None:
...
# Read components via queries
# Use ctx.views.* to read world
# Use ctx.commands.* to request updates


Important:

ctx.world is treated as read-only inside systems.

All component mutations and world commands go through ctx.commands.

3.2 WorldViewsHandle

Read-only accessors for world data, defined as part of WorldContext SOT:

Examples (conceptual):

ctx.views.visibility

iter_visible_agents(agent_id) -> Iterable[EntityID]

can_see(agent_id, target_id) -> bool

ctx.views.rooms

agents_in_room(room_id) -> Iterable[EntityID]

room_neighbors(room_id) -> Iterable[RoomID]

ctx.views.nav

find_path(room_id, start_pos, goal_pos) -> Path

ctx.views.interaction

nearby_assets(agent_id) -> Iterable[AssetID]

asset_state(asset_id) -> AssetSnapshot

Systems never hold references to world objects, only view data.

3.3 ECSCommandBuffer

Deterministic mutation requests (Sim4 / Sprint 2 shape, aligned with implementation):

```python
@dataclass
class ECSCommandBuffer:
    """
    Deterministic command buffer for ECS systems.

    - Assigns a monotonically increasing sequence number (seq), starting at 0.
    - Provides convenience methods to enqueue canonical ECSCommand instances.
    - Exposes a defensive copy of the queued commands via the `commands` property.
    """

    _next_seq: int = 0
    _commands: list[ECSCommand] = field(default_factory=list)

    @property
    def commands(self) -> list[ECSCommand]:
        # Defensive copy; mutating the result does not affect internal state.
        return list(self._commands)

    def set_component(self, entity_id, component_instance) -> None: ...
    def set_field(self, entity_id, component_type, field_name: str, value) -> None: ...
    def add_component(self, entity_id, component_instance) -> None: ...
    def remove_component(self, entity_id, component_type) -> None: ...
    def create_entity(self, components: list[object] | None = None) -> None: ...
    def destroy_entity(self, entity_id) -> None: ...
```

Notes:
- `archetype_code` is not part of the buffer API in Sim4; archetypes are inferred by `ECSWorld` from component sets.
- Monotonicity invariant: within a buffer instance, commands receive seq values `0, 1, 2, ...` in the order enqueued — no gaps or duplicates.
- The runtime later calls `ECSWorld.apply_commands(buffer.commands)` in Phase E, which sorts by `seq` for global determinism.

Future extension (not implemented in Sprint 2):

```python
def emit_world_command(self, command): ...  # reserved for future world-layer commands
```

This hook is reserved for phases where ECS systems also emit world‑layer commands; it is intentionally out of scope for the Sim4 Sprint 2 prototype and is not present in the current code.

Pipeline rule reaffirmed: Systems enqueue ECSCommands into an `ECSCommandBuffer` during Phases B–D; the runtime passes `buffer.commands` to `ECSWorld.apply_commands()` in Phase E, which applies all ECS mutations in a deterministic, seq‑sorted order. Systems do not call `ECSWorld` mutators directly during the tick.

4. Tick Phases & System Assignment

Per SOP-200 and SOT-RUNTIME-TICK, systems are grouped into phases:

Phase B: Perception

PerceptionSystem

Phase C: Cognition (non-LLM)

CognitivePreprocessor

EmotionGradientSystem

DriveUpdateSystem

MotiveFormationSystem

PlanResolutionSystem

SocialUpdateSystem

optional MaintenanceSystem (if introduced later)

Phase D: Intention & Resolution

IntentResolverSystem

MovementResolutionSystem

InteractionResolutionSystem

InventorySystem (if used as part of intent/interaction prep)

Phase E: Command Application & Execution

Runtime’s command-application pass (internal).

ActionExecutionSystem (scheduled here in Sim4 and the only ECS system in this phase):

reads intents and path state,

emits ECS and world commands via the buffer,

all effects are applied within Phase E through the same deterministic command-application pass.

ecs/systems/scheduler_order.py is the canonical registry:

PHASE_B_SYSTEMS = [
"PerceptionSystem",
]

PHASE_C_SYSTEMS = [
"CognitivePreprocessor",
"EmotionGradientSystem",
"DriveUpdateSystem",
"MotiveFormationSystem",
"PlanResolutionSystem",
"SocialUpdateSystem",
# "MaintenanceSystem",  # if/when added
]

PHASE_D_SYSTEMS = [
"IntentResolverSystem",
"MovementResolutionSystem",
"InteractionResolutionSystem",
"InventorySystem",     # optional
]

PHASE_E_SYSTEMS = [
"ActionExecutionSystem",
]


Runtime uses this mapping to drive the tick.

5. Canonical Systems

Below: each system’s purpose, main inputs (components + views), main outputs (commands / affected components), and mind layers.

I’m keeping this at the “architect spec” level, not per-line algorithm.

5.1 PerceptionSystem (perception_system.py, Phase B)

Goal: Update perception & attention substrates based on current world geometry and positions.

Reads:

Components:

Transform, RoomPresence (L1),

ProfileTraits (for perception range/attention tendencies),

previous PerceptionSubstrate, AttentionSlots, SalienceState.

WorldViews:

visibility (who/what is visible),

rooms (occupants, neighbors).

Writes (via commands):

PerceptionSubstrate

visible_agents, visible_assets, visible_rooms, proximity_scores.

AttentionSlots

focus on one agent/asset/room, maintain secondary_targets, update distraction_level.

SalienceState

numeric salience for agents, topics, locations.

Mind layers: L1/L2.

5.2 CognitivePreprocessor (cognitive_preprocessor.py, Phase C)

Goal: Deterministically adjust belief substrate based on perception & recent events; no semantics.

Reads:

Components:

BeliefGraphSubstrate,

AgentInferenceState,

PerceptionSubstrate, SalienceState.

Tick-local:

numeric summaries of last tick events (if passed in context).

Writes (via commands):

BeliefGraphSubstrate

adjust edge weights (propagation, decay, reinforcement).

AgentInferenceState

update pending_updates, uncertainty_score, epistemic_drift, last_inference_tick.

Mind layer: L3 (belief substrate).

5.3 EmotionGradientSystem (emotion_gradient_system.py, Phase C)

Goal: Evolve emotion fields smoothly over time based on events & drives.

Reads:

Components:

EmotionFields,

DriveState.

Optional numeric event signals (e.g. “conflict_intensity”, “praise_intensity”).

Writes (via commands):

EmotionFields

update tension, mood_valence, arousal, social_stress, excitement, boredom.

apply decay / diffusion rules.

Mind layer: L4.

5.4 DriveUpdateSystem (drive_update_system.py, Phase C)

Goal: Update drives based on internal state and environment; clamp to valid ranges.

Reads:

Components:

DriveState,

EmotionFields,

MotiveSubstrate (for goal satisfaction/unsatisfied drives).

WorldViews:

optional aggregate cues (e.g. crowd density, environmental stress metrics).

Writes (via commands):

DriveState

adjust each drive (curiosity, safety, attachment, etc.) with:

decay,

feedback from emotion,

satisfaction when related motives are progressing.

Mind layer: L4.

5.5 MotiveFormationSystem (motive_formation_system.py, Phase C)

Goal: Turn drive vector + beliefs + social signals into active numeric motives.

Reads:

Components:

DriveState,

BeliefGraphSubstrate,

SocialSubstrate, SocialBeliefWeights,

SelfModelSubstrate,

EmotionFields.

Optional:

PersonaSubstrate (if used) for aesthetic/identity-flavored motives.

Writes (via commands):

MotiveSubstrate

set active_motives (hashed motive IDs),

set motive_strengths,

update last_update_tick.

Mind layer: L5 (drive → motive).

5.6 PlanResolutionSystem (plan_resolution_system.py, Phase C)

Goal: Maintain & revise structural plans based on motives and feasibility.

Reads:

Components:

MotiveSubstrate,

PlanLayerSubstrate,

Transform, RoomPresence, PathState.

WorldViews:

nav and rooms to check reachability and constraints.

Writes (via commands):

PlanLayerSubstrate

update steps, current_index,

set revision_needed,

update plan_confidence.

Mind layer: L5 (plans).

5.7 SocialUpdateSystem (social_update_system.py, Phase C)

Goal: Update numeric social substrates (friendship, rivalry, loyalty, etc.).

Reads:

Components:

SocialSubstrate,

SocialImpressionState,

FactionAffinityState,

DriveState,

EmotionFields,

SocialBeliefWeights.

Tick-local:

recent interaction outcomes (e.g. “agent A helped agent B” encoded numerically).

Writes (via commands):

SocialSubstrate

adjust relationship_to, trust_to, respect_to, resentment_to.

SocialImpressionState

update impression_code_to, misunderstanding_level_to.

FactionAffinityState

adjust faction_affinity, faction_loyalty.

Mind layers: L3 + L4.

5.8 IntentResolverSystem (intent_resolver_system.py, Phase D)

Goal: Convert primitive suggestions (narrative/player/scenario) + plan state into SanitizedIntent that is physics-safe and allowed.

Reads:

Components:

PrimitiveIntent,

SanitizedIntent (previous tick value),

MotiveSubstrate, PlanLayerSubstrate,

DriveState,

Transform, RoomPresence.

WorldViews:

rooms & interaction for reachability and permissions (e.g. can talk to someone in another room?).

Writes (via commands):

SanitizedIntent

set valid, reason_code,

copy/transform target fields from PrimitiveIntent.

Optional:

mark PrimitiveIntent as consumed/processed (if we encode such status).

Mind layer: L5 → Intention bridge.

5.9 MovementResolutionSystem (movement_resolution_system.py, Phase D)

Goal: Translate sanitized intent into movement substrates and path updates.

Reads:

Components:

SanitizedIntent,

Transform, RoomPresence, PathState,

MovementIntent,

ActionState,

ProfileTraits (for movement speeds, cautiousness).

WorldViews:

nav (paths, blocked links),

rooms (neighbors, occupancy).

Writes (via commands):

MovementIntent

set kind_code, target_room_id, target_position, follow_agent_id, speed_scalar, active.

PathState

compute/update path, current_index, progress_along_segment, path_valid.

ActionState

set mode_code to WALKING/WAITING/STUCK,

update time_in_mode/last_mode_change_tick (symbolically via commands).

Mind layers: L1/L5 (body-level execution pipeline).

5.10 InteractionResolutionSystem (interaction_resolution_system.py, Phase D)

Goal: Resolve non-movement interactions and encode them as interaction intents + world commands.

Reads:

Components:

SanitizedIntent,

InteractionIntent,

Transform, RoomPresence,

InventorySubstrate, ItemState,

ActionState.

WorldViews:

interaction (nearby assets, doors, machines),

rooms (who is co-located).

Writes (via commands):

InteractionIntent

set kind_code, targets, strength_scalar, active.

ActionState

set mode_code to TALKING/INTERACTING where appropriate.

commands.emit_world_command(...)

e.g. OpenDoor, ToggleAsset, SpawnItem, DespawnItem requests (applied in Phase F).

Mind layer: L1/L5.

5.11 InventorySystem (inventory_system.py, Phase D, optional)

Goal: Maintain inventory substrate consistency around intents and interactions.

Reads:

Components:

InventorySubstrate,

ItemState,

InteractionIntent,

ActionState.

Writes (via commands):

InventorySubstrate, ItemState

queue updates for pickups, drops, equipping/unequipping

note: actual world placement of items happens in world layer; ECS only manages structural side.

Mind layer: L1 context.

5.12 ActionExecutionSystem (action_execution_system.py, Phase E)

Goal: Compute final agent-side consequences of movement & interactions and emit world commands, as part of the ECS mutation phase.

Reads:

Components:

MovementIntent, PathState,

InteractionIntent,

ActionState,

Transform, RoomPresence,

InventorySubstrate, ItemState,

optional meta/debug components.

WorldViews:

may use simplified nav/rooms to validate final placement (read-only).

Writes (via commands):

ECS-side:

Transform, RoomPresence:

update agent positions/rooms based on MovementIntent & path.

PathState:

mark segments complete, clear path when done.

ActionState:

update mode/time in mode after completion.

InventorySubstrate, ItemState:

finalize agent-side item states (e.g. once world confirms possession).

World-side (as commands):

MoveAgent, SetAgentRoom, OpenDoor, SpawnItem, DespawnItem, etc.

Mind layer: L1 (embodiment) with bridging commands to world.

Note: Although scheduled in Phase E, it still uses ECSCommandBuffer so all effects remain deterministic and recorded.

6. Determinism & Ordering Rules
   6.1 scheduler_order.py is Canonical

All ordering is explicit:

Systems are named and listed under phase-specific arrays.

Runtime uses exactly these lists to drive Phase B–E passes.

6.2 No Implicit Order

Systems cannot depend on “some other system happened before” unless that dependency is captured in scheduler_order.py.

Reordering systems requires:

updating this SOT,

updating scheduler_order.py,

optionally bumping a minor engine version.

6.3 RNG & Iteration

Any stochastic behavior must use ctx.rng only.

For entity iteration:

prefer stable ordering via entity IDs or storage index.

avoid relying on dict iteration order without explicit sorting.

7. Extending / Adding Systems

To add a new ECS system (e.g. PersuasionSystem or CrowdDynamicsSystem) you must:

Update this SOT:

describe purpose, inputs, outputs, phase, and mind-layer mapping.

Register in scheduler_order.py:

place in the correct phase with a clearly defined position relative to existing systems.

Respect constraints:

no world/narrative imports,

deterministic,

substrate-only logic,

no direct ECS mutation outside Phase E (and even there, prefer command-buffer pattern).

8. Completion Condition for SOT-SIM4-ECS-SYSTEMS

This SOT is considered implemented and respected when:

ecs/systems/ matches the layout and naming described here.

Each system:

accepts a SystemContext,

reads only from ctx.world and ctx.views.*,

writes only via ctx.commands,

runs in the phase assigned in scheduler_order.py.

Runtime:

invokes systems strictly according to phase & order in scheduler_order.py,

applies ECS commands only in Phase E,

applies world commands only in Phase F via WorldContext.

The combined system set:

implements all substrate flows described in SOP-300,

respects the 7-layer mind split and Free Agent Spec,

remains portable to a Rust ECS with equivalent semantics.

At that point, ECS systems form a clean, deterministic “nervous system” for the substrate mind:
Perception → Cognition → Intention → Embodied Action,
all under the SimX safety rails.