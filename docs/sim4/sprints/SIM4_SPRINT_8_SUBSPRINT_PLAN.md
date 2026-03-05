Sprint 8 – Sub-sprint breakdown

High-level goal:

“Wire in the narrative-facing adapters, even if narrative calls are stubs.”

We’ll interpret the earlier “narrative/runtime_context.py” as a slip and stick to the SOT naming:

backend/sim4/runtime/narrative_context.py = runtime bridge + DTOs

backend/sim4/narrative/interface.py = narrative sidecar interface

🔹 8.1 — DTO Completion & Narrative Interface Scaffolding

Goal
Define all runtime↔narrative DTOs in one place and expose a stub NarrativeEngineInterface so both sides compile cleanly without any LLM logic.

Files

backend/sim4/runtime/narrative_context.py

backend/sim4/runtime/__init__.py

backend/sim4/narrative/interface.py

Tests: backend/sim4/tests/narrative/test_narrative_interface_dtos.py (or similar)

Scope

DTOs in runtime (per SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT §4):

Ensure NarrativeTickContext (already added) is present and correct.

Add (if missing):

NarrativeBudget

NarrativeTickOutput

SubstrateSuggestion

StoryFragment

MemoryUpdate

NarrativeEpisodeContext

NarrativeEpisodeOutput

NarrativeUICallContext

NarrativeUIText

All as frozen/primitive/Rust-portable dataclasses.

Exports

Re-export these DTOs from backend/sim4/runtime/__init__.py so narrative/ can import them without touching engine internals.

Narrative interface stub

Create backend/sim4/narrative/interface.py with:

class NarrativeEngineInterface: defining:

run_tick_jobs(ctx: NarrativeTickContext) -> NarrativeTickOutput

summarize_episode(ctx: NarrativeEpisodeContext) -> NarrativeEpisodeOutput

describe_scene(ctx: NarrativeUICallContext) -> NarrativeUIText

A simple NullNarrativeEngine(NarrativeEngineInterface) implementation that:

Returns empty NarrativeTickOutput (no suggestions, no story, no memory).

Returns placeholder strings for episode and UI text (e.g. "TODO: narrative not implemented").

Tests

Sanity tests that:

DTOs can be constructed with minimal dummy values.

NullNarrativeEngine.run_tick_jobs returns the right types and empty lists.

NullNarrativeEngine.summarize_episode and describe_scene return NarrativeEpisodeOutput/NarrativeUIText with non-None text.

Exit criteria

✅ All DTOs from SOT §4 exist, with correct field names/types.

✅ runtime.__init__ exposes these DTOs.

✅ NarrativeEngineInterface & NullNarrativeEngine compile and import without circular deps.

✅ Tests confirm the basic call signatures and shapes.

🔹 8.2 — Implement NarrativeRuntimeContext (Runtime Bridge, Still Stub Engine)

Goal
Implement the runtime bridge class that builds the narrative contexts and calls NarrativeEngineInterface, but still with NullNarrativeEngine by default (no real narrative yet).

Files

backend/sim4/runtime/narrative_context.py

Possibly backend/sim4/runtime/history.py (or a small adapter if you already have history)

Tests: backend/sim4/tests/narrative/test_narrative_runtime_context.py

Scope

Add NarrativeRuntimeContext class (per SOT §5) with:

__init__(engine, history, budget_config)

build_tick_context(...) -> NarrativeTickContext

run_tick_narrative(...) -> None

For Sprint 8:

Use existing WorldSnapshot builder and AgentSnapshot access.

Consume diff_summary from history/Phase H (but do not recompute diffs).

Use NullNarrativeEngine in tests (and maybe as default in code).

Exit criteria

✅ NarrativeRuntimeContext.build_tick_context produces a valid NarrativeTickContext with:

world_snapshot from build_world_snapshot

agent_snapshots list

diff_summary (dummy or from a stub history)

✅ run_tick_narrative:

Respects a simple budget (e.g. skip if disabled).

Calls engine.run_tick_jobs.

For now, just logs or stores outputs via history stubs; no real ECS commands yet.

✅ Unit tests with fake WorldContext/ECSWorld and fake history.

🔹 8.3 — Tick() Phase I Wiring & Minimal End-to-End Test

Goal
Hook the narrative runtime context into the tick loop’s Phase I so we have a real call path:

tick() → Phase I → NarrativeRuntimeContext.run_tick_narrative(...) → NullNarrativeEngine.

Files

backend/sim4/runtime/tick_loop.py (or whatever your tick driver is)

backend/sim4/runtime/narrative_context.py (minor adjustments)

Tests: backend/sim4/tests/runtime/test_tick_with_narrative_stub.py

Scope

In the main tick pipeline (per SOT-SIM4-RUNTIME-TICK):

Instantiate NarrativeRuntimeContext (probably in some Runtime or Engine ctor).

In Phase I (post-diff/history), call run_tick_narrative(...).

Use NullNarrativeEngine by default, so:

No ECS/world behavior changes.

No tokens, no external calls.

Exit criteria

✅ tick loop runs end-to-end with narrative hooked in without changing simulation results.

✅ A test confirms:

run_tick_narrative gets called at the right phase.

Simulation still runs when narrative is disabled or NullNarrativeEngine is used.

✅ No imports from narrative/ leak into ECS/world/snapshot — only runtime depends on narrative interface.

🔹 8.4 — Episode/UI Context Stubs (Optional for Sprint 8)

Goal
Set up minimal episode/UI paths so later narrative work can call into them without structural changes.

Scope

Implement basic constructor helpers for:

NarrativeEpisodeContext (given StageEpisodeV2 + final snapshot).

NarrativeUICallContext (given a UI request).

Add stubs for NarrativeRuntimeContext.summarize_episode / describe_scene that:

Construct contexts.

Call engine.summarize_episode / describe_scene.

Exit criteria

✅ Episode/UI narrative call sites compile and are test-covered with stubs.

✅ Still no actual LLM or semantic logic.