📘 SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT

Runtime ↔ Narrative Bridge, Substrate Suggestion Application & Replay
Draft 1.0 — Architect-Level, SOP-100/200/300 Compliant

0. Scope & Purpose

This SOT defines the runtime-side narrative bridge for Sim4:

Where and how narrative contexts (tick/episode/UI) are built.

How runtime calls the NarrativeEngineInterface defined in narrative/interface.py.

How SubstrateSuggestion, StoryFragment, and MemoryUpdate outputs are:

validated,

logged for replay,

converted into ECS/world commands (for future ticks only).

It is responsible for:

Constructing NarrativeTickContext, NarrativeEpisodeContext, and NarrativeUICallContext.

Applying narrative outputs in a way that:

respects SOP-200 determinism,

preserves layer boundaries (SOP-100),

adheres to SOP-300 (L1–L7 split),

stays within Sim4 engine SOTs:

SOT-SIM4-ENGINE

SOT-SIM4-RUNTIME-TICK

SOT-SIM4-WORLD-ENGINE

SOT-SIM4-ECS-CORE / ECS-SUBSTRATE-COMPONENTS / ECS-SYSTEMS

SOT-SIM4-NARRATIVE-INTERFACE

This SOT does not define:

Narrative logic itself (LLM prompts, semantic reasoning) — that is in narrative/.

UI rendering of story text — that is in snapshot/episode & frontend SOTs.

World/episode type definitions — those belong to snapshot/world SOTs.

This doc is the single source of truth for how runtime packages data for narrative and applies narrative outputs back into the simulation.

---

## Status — Sprint 8 (Runtime ↔ Narrative Bridge)

Implemented in Sim4:

- Runtime-owned DTOs (per §4):
  - NarrativeBudget, NarrativeTickContext, NarrativeTickOutput,
  - SubstrateSuggestion, StoryFragment, MemoryUpdate,
  - NarrativeEpisodeContext, NarrativeEpisodeOutput,
  - NarrativeUICallContext, NarrativeUIText.
- NarrativeRuntimeContext bridge with:
  - build_tick_context(...): constructs WorldSnapshot and agent_snapshots via snapshot builder and consumes diff_summary from history (derived from SnapshotDiff via snapshot.summarize_diff_for_narrative). No recomputation of diffs here.
  - run_tick_narrative(...): applies budget/stride gating, calls NarrativeEngineInterface.run_tick_jobs(...), and logs outputs to history. No ECS/world mutations; suggestions are not yet converted to ECS commands in Sprint 8.
- Phase I narrative trigger in runtime.tick(...): when a NarrativeRuntimeContext is provided, tick() calls NarrativeRuntimeContext.run_tick_narrative(...) exactly once per tick after Phase H (history/diff). The call is wrapped defensively so narrative failures never affect the deterministic kernel.

Out of scope / deferred:

- Real narrative logic (LLM calls, semantic reasoning) — currently using NullNarrativeEngine stub.
- Application of SubstrateSuggestion into ECS commands (e.g., PrimitiveIntent, NarrativeState updates) — to be implemented in a later sprint.
- Episode-level and UI-level narrative wiring beyond DTO definitions (NarrativeEpisodeContext/NarrativeUICallContext lifecycles).

These items are documented here as planned interfaces; their behavior will be delivered in subsequent sprints without changing the contracts established in this SOT.

1. Position in the 6-Layer DAG

DAG reminder:

runtime   →   ecs   →   world   →   snapshot   →   integration
↑
narrative (sidecar)


Within this DAG:

runtime/narrative_context.py sits squarely in runtime, above ECS + world, adjacent to runtime/world_context.py and tick driver code.

It can import:

runtime/world_context.py

ECS API (ecs/world.py, ecs/components/*)

snapshot/episode types

narrative/interface.py (the façade)

It must not be imported by:

ecs/

world/

snapshot/

integration/

narrative/ (other than DTO type imports, see below).

The data types defined here (NarrativeTickContext, etc.) are DTOs:

Owned by runtime.

Imported by narrative/interface.py and/or narrative/adapters.py.

Free of engine handles (only plain data structures).

2. File Layout

Runtime narrative bridge lives here:

runtime/
narrative_context.py  # NarrativeRuntimeContext, DTOs, bridge logic
world_context.py      # (per SOT-SIM4-RUNTIME-WORLD-CONTEXT)
tick_loop.py          # main tick driver (per SOT-SIM4-RUNTIME-TICK)
history.py            # tick/episode history & replay logs


This SOT governs only runtime/narrative_context.py, but assumes:

world_context.py provides WorldContext, WorldViews, event buffers.

snapshot SOT provides WorldSnapshot, AgentSnapshot, StageEpisodeV2.

3. Responsibilities of runtime/narrative_context.py

narrative_context.py is responsible for:

DTO Definitions

Canonical home for:

NarrativeTickContext

NarrativeTickOutput (import shape aligned with SOT-SIM4-NARRATIVE-INTERFACE)

SubstrateSuggestion

StoryFragment

MemoryUpdate

NarrativeEpisodeContext, NarrativeEpisodeOutput

NarrativeUICallContext, NarrativeUIText

NarrativeBudget

These are plain dataclasses with Rust-portable fields.

Runtime Narrative Bridge

NarrativeRuntimeContext (or similar) that:

builds the contexts for narrative from WorldContext, ECSWorld, and history,

calls NarrativeEngineInterface,

validates & logs narrative outputs,

translates SubstrateSuggestions into ECS commands and memory operations scheduled for future ticks.

Replay & Logging Glue

Stores narrative outputs into history structures for:

debugging (trace),

full simulation replay without re-calling narrative.

Budget & Policy Enforcement (Runtime Side)

Applies high-level budgets:

NarrativeBudget per tick/episode/UI call,

global toggles (disable narrative, reduce frequency, etc.).

Narrative itself still enforces detailed safety/policy in narrative/policy.py; runtime acts as a coarse budget gate and output validator.

4. DTOs: Narrative Context & Output Types
   4.1 NarrativeBudget
   @dataclass
   class NarrativeBudget:
   max_tokens: int
   max_ms: int
   allow_external_calls: bool
   tick_stride: int = 1  # run narrative every N ticks (>= 1)


Defined and owned by runtime.

Passed down to narrative as part of each context.

4.2 NarrativeTickContext (Input → Narrative)
@dataclass
class NarrativeTickContext:
tick_index: int
dt: float
episode_id: int
world_snapshot: "WorldSnapshot"
agent_snapshots: list["AgentSnapshot"]
recent_events: list["WorldEvent"]
diff_summary: dict
narrative_budget: NarrativeBudget


Notes:

WorldSnapshot, AgentSnapshot, WorldEvent are defined in snapshot/world SOTs and imported here.

Contains no ECSWorld or WorldContext handles.

diff_summary

• Definition: compact, JSON‑like dict derived from the snapshot diff layer. Runtime (via history/Phase H) computes a SnapshotDiff between the last two WorldSnapshots and compresses it using a fixed helper in the snapshot package (e.g., summarize_diff_for_narrative).

• Purpose: encode per‑tick changes relevant to narrative/UI — agent room changes, position changes, and item spawn/despawn/moves — in a small, stable structure suitable for LLM consumption and Rust interop.

• Contract: read‑only input for narrative. Narrative never mutates or re‑computes diffs; it only consumes diff_summary. All write‑backs still occur exclusively via SubstrateSuggestion / StoryFragment / MemoryUpdate.

Implementation note (Sprint 8): The tick pipeline’s Phase I is wired to NarrativeRuntimeContext.run_tick_narrative(...). A stub engine (NullNarrativeEngine) may be provided by composition to keep the sidecar inert by default.

4.3 NarrativeTickOutput (Output ← Narrative)

Per SOT-SIM4-NARRATIVE-INTERFACE:

@dataclass
class NarrativeTickOutput:
substrate_suggestions: list["SubstrateSuggestion"]
story_fragments: list["StoryFragment"]
memory_updates: list["MemoryUpdate"]

4.3.1 SubstrateSuggestion

Runtime canonical shape:

@dataclass(frozen=True)
class SubstrateSuggestion:
kind: str                  # "PrimitiveIntent", "NarrativeStateUpdate"
agent_id: int | None       # EntityID as int
payload: dict              # plain JSON-like structure


Runtime is responsible for:

validating agent_id,

mapping payload to known ECS components & fields.

4.3.2 StoryFragment
@dataclass(frozen=True)
class StoryFragment:
scope: str                # "tick", "agent", "room", "global"
agent_id: int | None
room_id: int | None
text: str
importance: float         # 0–1


Runtime forwards this to history/snapshot layer for UI; no mechanical effect.

4.3.3 MemoryUpdate
@dataclass(frozen=True)
class MemoryUpdate:
operation: str            # "UPSERT_SUMMARY", "UPSERT_EVENT", ...
key: int                  # external memory key
payload: dict


Runtime calls narrative.memory_store (or equivalent) with this.

4.4 Episode & UI Contexts

Minimal shapes (referenced by SOT-SIM4-NARRATIVE-INTERFACE):

@dataclass
class NarrativeEpisodeContext:
episode_id: int
world_snapshot: "WorldSnapshot"
episode: "StageEpisodeV2"
history_slice: "EpisodeHistorySlice"
narrative_budget: NarrativeBudget

@dataclass
class NarrativeEpisodeOutput:
summary_text: str
character_summaries: dict[int, str]   # agent_id -> text
key_moments: list[str]
memory_updates: list[MemoryUpdate]

@dataclass
class NarrativeUICallContext:
scope: str              # "agent", "room", "scene"
agent_id: int | None
room_id: int | None
world_snapshot: "WorldSnapshot"
narrative_budget: NarrativeBudget

@dataclass
class NarrativeUIText:
text: str

5. NarrativeRuntimeContext (Bridge Class)
   5.1 Shape
   class NarrativeRuntimeContext:
   def __init__(
   self,
   engine: "NarrativeEngineInterface",
   history: "HistoryBuffer",
   budget_config: "NarrativeBudgetConfig",
   ): ...

   def build_tick_context(
   self,
   tick_index: int,
   dt: float,
   episode_id: int,
   world_ctx: "WorldContext",
   ecs_world: "ECSWorld",
   ) -> NarrativeTickContext: ...

   def run_tick_narrative(
   self,
   tick_index: int,
   dt: float,
   episode_id: int,
   world_ctx: "WorldContext",
   ecs_world: "ECSWorld",
   external_command_sink: "ExternalCommandSink",
   ) -> None: ...

   def summarize_episode(
   self,
   ctx: NarrativeEpisodeContext,
   ) -> NarrativeEpisodeOutput: ...

   def describe_scene(
   self,
   ctx: NarrativeUICallContext,
   ) -> NarrativeUIText: ...


Where:

engine is an instance of NarrativeEngineInterface (from narrative/interface.py).

history is a runtime history buffer (per runtime/history SOT).

budget_config holds global/episode-level budget settings.

external_command_sink is the runtime input channel that schedules ECS commands for next tick’s Phase A.

5.2 Responsibilities per Method
5.2.1 build_tick_context(...)

Steps:

Construct WorldSnapshot from world_ctx + ecs_world using snapshot builder (as defined in snapshot/world SOTs).

Build AgentSnapshot list for all agents:

Pulls from ECS components only:

identity, drives, emotions, social, motives, plan, intent, action, narrative_state.

No ECS handles; just numeric/state views.

Fetch recent events and diff_summary from history/WorldContext (Phase G/H outputs). diff_summary is produced earlier in the tick by computing a SnapshotDiff between the last two WorldSnapshots in the snapshot layer and compressing it via a fixed helper (e.g., summarize_diff_for_narrative). narrative_context.py consumes this summary and does not recompute diffs itself.

Determine NarrativeBudget for this tick based on:

budget_config,

tick_index and tick_stride,

any episode-level caps.

Returns a fully-populated NarrativeTickContext.

5.2.2 run_tick_narrative(...)

Called only in Phase I (per SOT-SIM4-RUNTIME-TICK).

Workflow:

Respect NarrativeBudget:

If current tick is not on-budget (e.g. stride > 1 and tick_index % stride != 0), skip the call; no narrative run, no suggestions.

Build NarrativeTickContext via build_tick_context(...).

Call:

output = self.engine.run_tick_jobs(tick_ctx)


Pass output to:

_handle_tick_output_for_logging(output, tick_index, episode_id)

_apply_substrate_suggestions(output.substrate_suggestions, external_command_sink)

_apply_story_fragments(output.story_fragments, tick_index, episode_id)

_apply_memory_updates(output.memory_updates)

No ECS/world mutations happen inside this method; mutations are scheduled as commands via external_command_sink for next tick’s input phase.

Implementation note (Sprint 8): In Sim4, Phase I is integrated into runtime.tick(...) to call NarrativeRuntimeContext.run_tick_narrative(...) once per tick when a narrative context is provided. The default engine may be a stub (NullNarrativeEngine), and exceptions are contained to preserve deterministic kernel execution.

6. Mapping SubstrateSuggestion → ECS Commands
   6.1 ExternalCommandSink

Runtime’s input channel (conceptual):

class ExternalCommandSink:
def enqueue_ecs_command(self, cmd: "ECSCommand") -> None: ...


These commands are:

accumulated,

applied in Phase E of the next tick (per SOT-SIM4-RUNTIME-TICK),

thereby updating ECS components before systems run.

6.2 Handling "PrimitiveIntent" Suggestions

For each SubstrateSuggestion with kind == "PrimitiveIntent":

Validate agent_id:

Check that an entity with that EntityID exists in ecs_world.

If not, drop suggestion and log a warning event.

Validate payload keys:

Required: intent_code (int).

Optional: target_agent_id, target_room_id, target_asset_id, priority.

Sanitize values:

Clamp priority to [0, 1] (or configured range).

Ensure IDs are ints; if invalid, treat as None.

Create one or more ECSCommands, e.g.:

set_component(entity=agent_id, component_instance=PrimitiveIntent(...))
or

set_field on an existing PrimitiveIntent component.

Enqueue commands via external_command_sink.enqueue_ecs_command(...).

Result:

Narrative suggestions become fresh PrimitiveIntent components available to:

Phase B–D systems of the next tick, notably IntentResolverSystem.

6.3 Handling "NarrativeStateUpdate" Suggestions

For each SubstrateSuggestion with kind == "NarrativeStateUpdate":

Validate agent_id or handle agent-less narrative state as needed:

Usually per-agent; if None, this may refer to a global narrative state entity.

Validate payload keys:

Typical: narrative_id, cached_summary_ref, tokens_used_recently.

Build ECSCommands to update NarrativeState component:

If component exists:

set_field(entity, NarrativeState, "narrative_id", ...)

set_field(entity, NarrativeState, "cached_summary_ref", ...)

etc.

If component missing:

Optionally create it via add_component.

Enqueue via external_command_sink.

Constraint:
Only narrative may drive these updates; other systems treat NarrativeState as read-only.

6.4 Unknown or Invalid Kinds

If SubstrateSuggestion.kind is anything other than "PrimitiveIntent" or "NarrativeStateUpdate":

Runtime must:

ignore it,

log a diagnostic event,

(optionally) track metrics for unexpected suggestion kinds.

Adding new kinds requires updating:

SOT-SIM4-NARRATIVE-INTERFACE

SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT

narrative/interface.py & adapters.

7. Story Fragments & Memory Updates
   7.1 StoryFragments → History/UI

_apply_story_fragments(...) performs:

For each StoryFragment:

Attach metadata:

tick_index

episode_id

agent/room mapping validity.

Push into:

HistoryBuffer as narrative log entries.

Any snapshot/episode structure designated for narrative overlays.

No ECS mutations are created from StoryFragments.

7.2 MemoryUpdates → Memory Store

_apply_memory_updates(...) performs:

For each MemoryUpdate:

Call into narrative.memory_store (or a configured adapter) with:

operation, key, and payload.

Optionally update a local index so that:

NarrativeState.cached_summary_ref references are resolvable.

This memory store interaction:

has no direct effect on ECS or world,

is treated as a side effect outside the determinism guarantee unless memory outputs are logged.

8. Replay & Determinism
   8.1 Logging Narrative Outputs

NarrativeRuntimeContext must log:

For each tick where narrative runs:

tick_index, episode_id

full substrate_suggestions list (validated form)

optionally story_fragments and memory_updates

Log format must be:

stable,

JSON-serializable,

sufficient to replay all narrative effects on the substrate.

8.2 Replay Mode

In Replay Mode, runtime:

Does not call self.engine.run_tick_jobs().

Instead:

fetches pre-recorded substrate_suggestions from history.

feeds them through _apply_substrate_suggestions(...) using the same logic as in live runs.

This ensures:

numeric substrate evolution is deterministic conditional on logged narrative outputs.

narrative text generation can be:

re-run (for cosmetic reasons, not required for determinism),

or also replayed from logs.

9. Policy Integration & Failure Modes
   9.1 Budget & Frequency

NarrativeBudgetConfig (runtime-level) controls:

global on/off switches for narrative,

tick stride (e.g. every 5 ticks),

max tokens / time per episode or per run.

NarrativeRuntimeContext must:

consult budget_config before every call,

skip narrative calls when budget is exhausted and treat that tick as “no suggestions”.

9.2 Defensive Behavior

If NarrativeEngineInterface:

throws an exception,

returns malformed outputs,

times out,

then NarrativeRuntimeContext must:

treat this as “no suggestions” for that tick,

log an error event,

never crash the main simulation loop.

Substrate and world remain fully functional without narrative calls.

10. Extension Rules

Future Sim versions may extend this bridge by:

Adding new DTOs for new job types (e.g. NarrativeCharacterArcContext).

Adding new SubstrateSuggestion.kind branches, provided:

they map to well-defined ECS commands,

they never bypass PrimitiveIntent and NarrativeState without updating ECS SOTs.

It must not:

allow narrative to enqueue arbitrary ECSCommands directly.

allow narrative to write drives/emotions/beliefs directly without going through agreed suggestion kinds and ECS systems.

11. Completion Conditions for SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT

This SOT is considered implemented and enforced when:

runtime/narrative_context.py:

defines all DTOs described in §4 (or imports them from a dedicated runtime/narrative_schema.py),

defines NarrativeRuntimeContext with methods in §5.

The main tick loop (per SOT-SIM4-RUNTIME-TICK):

calls NarrativeRuntimeContext.run_tick_narrative(...) only in Phase I,

never calls narrative anywhere else.

SubstrateSuggestion kinds:

exactly match the set defined in SOT-SIM4-NARRATIVE-INTERFACE for Sim4,

are all handled explicitly, with unknown kinds safely ignored and logged.

All narrative-driven ECS changes:

are expressed as ECSCommands through ExternalCommandSink,

are applied during Phase E of the next tick, before systems run,

affect only:

PrimitiveIntent,

NarrativeState,

any future approved substrate components.

Replay mode:

can re-run a simulation deterministically using stored narrative outputs without invoking LLMs.

No module in:

ecs/, world/, snapshot/, or integration/

imports runtime/narrative_context.py (one-way dependency: runtime → everything below, narrative sidecar remains separate).

At that point, the Runtime Narrative Context is:

Sim4-correct as the single bridge between deterministic core and semantic sidecar,

safe and replayable,

ready for Junie implementation sprints with clear responsibilities and no hidden cross-layer leaks.