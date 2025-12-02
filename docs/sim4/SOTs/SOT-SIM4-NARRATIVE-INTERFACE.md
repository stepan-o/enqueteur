# 📘 SOT-SIM4-NARRATIVE-INTERFACE
_**LLM / Semantic Sidecar, Substrate Interface & Tick Hooks**_  
**Draft 1.0 — Architect-Level, SOP-100/200/300 Compliant**

---

## 0. Scope & Purpose
This SOT defines the **narrative sidecar interface** for Sim4:
* How the **narrative layer** (LLM + semantic logic) connects to:
  * the deterministic simulation core (runtime + ECS + world),
  * snapshots & episodes,
  * the UI / Stage viewer.
* What **inputs** narrative receives (snapshots, events, numeric substrates).
* What **outputs** narrative is allowed to produce:
  * human-readable text (story, descriptions, logs),
  * structured semantic annotations,
  * constrained **intent suggestions** into the ECS substrate.
* What is **explicitly forbidden** for narrative (no direct mutation of ECS/world).

It is aligned with and must not contradict:
* **SOP-100** — Layer Boundary Protection.
* **SOP-200** — Determinism & Simulation Contract.
* **SOP-300** — 7-Layer Agent Mind & Free Agent Spec.
* **SOT-SIM4-ENGINE** — global folder/layout spec.
* **SOT-SIM4-RUNTIME-TICK** — tick phases (incl. Phase I: Narrative Trigger).
* **SOT-SIM4-RUNTIME-WORLD-CONTEXT** — WorldContext, WorldViews, WorldCommands.
* **SOT-SIM4-ECS-CORE**, **SOT-SIM4-ECS-SUBSTRATE-COMPONENTS**, **SOT-SIM4-ECS-SYSTEMS**.
* **SOT-SIM4-WORLD-ENGINE** — world identities, state, and views.

This SOT **does not** define:
* Prompt engineering details or LLM provider specifics.
* UI rendering logic (that lives in frontend & snapshot/episode SOTs).
* Full narrative content schemas (covered by snapshot/episode design and any separate narrative-content SOT).

This is the **single source of truth** for the _interface_ between narrative and the Sim4 engine core.

---

## 1. Position in the 6-Layer DAG & Boundaries
DAG (already locked):
```text
runtime   →   ecs   →   world   →   snapshot   →   integration
                ↑
              narrative (sidecar)
```

Within this DAG:
* `narrative/` is a **sidecar semantic layer**, responsible for:
  * turning numeric substrate + world state into stories, summaries, and labels,
  * suggesting **high-level intents** and reflection updates back into the substrate,
  * staying within safety and budget limits.
* `narrative/`:
  * **never imports:**
    * `ecs/`
    * `world/`
    * `runtime/`
    * `snapshot/`
    * `integration/`
  * interacts only through **plain data contracts** defined in this SOT and in:
    * `runtime/narrative_context.py` (or equivalent adapter),
    * snapshot/episode types (for read-only inputs).
* The engine core (runtime/ECS/world):
  * cannot import `narrative/` modules directly except for the **adapter façade** (e.g., `NarrativeEngineInterface`),
  * must treat narrative as an **external service**:
    * call out → get structured outputs → translate into ECS/world commands for future ticks.

Narrative is the **only place** in the engine where:
* free-form natural language appears,
* semantic interpretation of substrate fields occurs,
* L6–L7 mind-layer logic (reflection, persona, story) is implemented.

---

## 2. Folder Layout for narrative/ (Sim4)

Canonical structure (must match **SOT-SIM4-ENGINE**):
```text
narrative/
    interface.py        # NarrativeEngineInterface — main entry points used by runtime
    jobs.py             # NarrativeJob definitions (tick-level, episodic, ad-hoc)
    adapters.py         # Builders/parsers between engine data and narrative IO schemas
    policy.py           # Safety, throttling, budget rules
    memory_store.py     # Handles for external semantic memory/log stores
    prompts/            # Prompt templates (if local) or config
        __init__.py
        tick_prompts.py
        episode_prompts.py
        ui_prompts.py
    trace.py            # Optional: tracing/logging of narrative calls & outputs
```

Notes:
* `interface.py` exposes the **only API** that runtime uses.
* `adapters.py` defines **pure data transforms** between:
  * engine-level inputs (snapshots, events, substrate views),
  * LLM-ready narrative inputs/outputs.
* No module in `narrative/` imports ECS or world types directly; all shapes are **DTO-style schemas** defined in runtime/snapshot SOTs.

---

## 3. Narrative Roles in Sim4
The narrative sidecar has three canonical roles:
1. **Substrate Coach (L6/L7 → L1–L5 via intents)**
   * Reads: snapshots + numeric substrates.
   * Outputs: **PrimitiveIntent** suggestions and **NarrativeState** updates (via structured outputs).
2. **Storyteller (UI / Episode Output)**
   * Reads: snapshots, episode structures, world events.
   * Outputs: human-readable text:
     * scene descriptions,
     * character summaries,
     * episode recaps,
     * tooltips for the UI.
Archivist (Semantic Memory)
   * Reads: snapshots, events, existing semantic memory.
   * Outputs: semantic entries (summaries, embeddings, narrative IDs) stored via `memory_store.py`, referenced from `NarrativeState.cached_summary_ref`.

All three roles are implemented via NarrativeJobs executed by the runtime at specific hooks.

---

## 4. Runtime ↔ Narrative Call Points (Tick & Episodic)

Per **SOT-SIM4-RUNTIME-TICK**, the main tick pipeline is:

```text
tick(dt):
  1. Lock WorldContext
  2. Update Clock
  3. Phase A: Input Processing
  4. Phase B: Perception
  5. Phase C: Cognition (non-LLM)
  6. Phase D: Intention → ECS Commands
  7. Phase E: ECS Command Application
  8. Phase F: World Updates
  9. Phase G: Event Consolidation
 10. Phase H: Diff Recording + History
 11. Phase I: Narrative Trigger (post-tick)
 12. Unlock WorldContext
```

Narrative interfaces with this pipeline as follows:

---

### 4.1 Phase I — Tick-Level Narrative Trigger

After **Phase H** (diff recording), runtime:
1. Builds a **NarrativeTickContext** (see §5.1).
2. Calls:
```python
narrative_engine.run_tick_jobs(ctx: NarrativeTickContext) -> NarrativeTickOutput
```
3. This may yield:
   * **SubstrateSuggestions** (intent suggestions, reflection updates),
   * **StoryFragments** (optional per-tick narrative text),
   * **MemoryUpdates** (semantic summaries to store externally).
4. Runtime **must not** apply any ECS/world mutations from this call directly.  
Instead:
* it converts `SubstrateSuggestions` into:
  * ECS commands targeting:
    * `PrimitiveIntent` components (for next tick’s Phase A),
    * `NarrativeState` components,
* queued for the **next tick** (**Phase A** input processing).

Narrative thus influences **future ticks only**, never retroactively.

---

## 4.2 Episodic / Scene-Level Calls
At higher-level episode boundaries (e.g., end of `StageEpisodeV2`), runtime may call:
```python
narrative_engine.summarize_episode(ep_ctx: NarrativeEpisodeContext) -> NarrativeEpisodeOutput
```

* Inputs: final episode snapshots, event history, existing semantic memory.
* Outputs: human-readable episode summary, character profiles, “previously on…” recap, plus optional memory updates.

These calls:
* are not part of the core determinism contract,
* may be disabled or rate-limited without affecting numeric substrate correctness.

---

### 4.3 On-Demand UI Narration
The UI (via integration layer) may request ad-hoc narration:
```python
narrative_engine.describe_scene(ui_ctx: NarrativeUICallContext) -> NarrativeUIText
```

* Example: when the user clicks a character, the UI requests a short “who is this?” blurb.

These calls are **purely cosmetic** and have **no write-back** to ECS/world.

---

## 5. Narrative Input & Output Schemas
All narrative I/O is defined as **plain dataclasses / dict-like structures** in runtime/snapshot SOTs or in `narrative/adapters.py`. Narrative code sees only these schemas, not engine internals.

---

### 5.1 NarrativeTickContext (Input)

Shape (conceptual, defined in runtime):


```python
@dataclass
class NarrativeTickContext:
    tick_index: int
    dt: float
    episode_id: int
    world_snapshot: "WorldSnapshot"           # from snapshot/ SOT
    agent_snapshots: list["AgentSnapshot"]    # numeric substrate views per agent
    recent_events: list["WorldEvent"]         # from world/events.py
    diff_summary: dict
    """
    Compact, lossy summary of last-tick changes derived from SnapshotDiff
    (snapshot/diff_types.py). Shape is intentionally simple and JSON-like
    for Rust/LLM portability. Narrative never sees raw SnapshotDiff, only
    this summarized view.
    """
    narrative_budget: "NarrativeBudget"       # tokens/time limits for this call
```

Notes:
* `AgentSnapshot` is a numeric view derived from ECS components (L1–L5 + NarrativeState references), not raw ECS.
* No ECS write handles are exposed; this is **read-only** from narrative’s perspective.

`diff_summary` is derived from `SnapshotDiff` (see SOT-SIM4-SNAPSHOT-AND-EPISODE §X.Y) by runtime/history.
Narrative sees only this compact summary, never the raw per-entity diff structures.  
This keeps narrative **decoupled from snapshot internals** while still acknowledging that the diff layer exists and feeds it.

---

### 5.2 NarrativeTickOutput (Output)
```python
@dataclass
class NarrativeTickOutput:
    substrate_suggestions: list["SubstrateSuggestion"]
    story_fragments: list["StoryFragment"]
    memory_updates: list["MemoryUpdate"]
```

Where:

#### 5.2.1 SubstrateSuggestion
This is the **only pathway** back into the substrate from tick-level narrative.

Canonical kinds for Sim4:
```python
@dataclass(frozen=True)
class SubstrateSuggestion:
    kind: str                  # "PrimitiveIntent", "NarrativeStateUpdate"
    agent_id: int | None       # EntityID, if agent-targeted
    payload: dict              # simple, Rust-portable data
```
* kind == `"PrimitiveIntent"`:
  * `payload` example:
```python
{
"intent_code": int,
"target_agent_id": int | None,
"target_room_id": int | None,
"target_asset_id": int | None,
"priority": float,
}
```
    * Runtime translates this into ECS commands to **set or create** a `PrimitiveIntent` component for that agent in **next tick’s Phase A**.
* `kind == "NarrativeStateUpdate"`:
  * `payload` example:
```python
{
"narrative_id": int,
"cached_summary_ref": int | None,
"tokens_used_recently": int,
}
```
    * Runtime translates this into ECS commands to update the agent’s `NarrativeState` component, respecting SOT-SIM4-ECS-SUBSTRATE-COMPONENTS (only narrative may write this).

For Sim4:
* **No other kinds** are allowed without updating this SOT.
* Narrative does **not** directly alter drives, emotions, or belief graphs; it nudges agents via `PrimitiveIntent`.

#### 5.2.2 StoryFragment
Human-readable narrative text:
```python
@dataclass(frozen=True)
class StoryFragment:
    scope: str          # "tick", "agent", "room", "global"
    agent_id: int | None
    room_id: int | None
    text: str           # full natural language
    importance: float   # 0–1 scoring for UI prioritization
```

Use:
* Stored by runtime or snapshot layer for UI log / overlays.
* Has **no mechanical effect** on substrate.

#### 5.2.3 MemoryUpdate
Semantic memory operations for the **Archivist** role:
```python
@dataclass(frozen=True)
class MemoryUpdate:
    operation: str       # "UPSERT_SUMMARY", "UPSERT_EVENT", ...
    key: int             # external store key (hash/int)
    payload: dict        # embedding refs, compressed text, tags
```
* `memory_store.py` implements the mapping from these to an external DB/log store.
* `NarrativeState.cached_summary_ref` points into this memory space.

---

## 6. Narrative Jobs & Orchestrator
### 6.1 NarrativeJob Definitions (`narrative/jobs.py`)
Sim4 defines a small set of **job types**:
* `TickJob` — runs in Phase I per tick.
* `EpisodeSummaryJob` — runs at episode/end-of-run.
* `UISceneDescribeJob` — runs on-demand from UI.

Shape:
```python
@dataclass
class NarrativeJob:
    kind: str               # "TickJob", "EpisodeSummaryJob", "UISceneDescribeJob"
    payload: dict           # context-dependent data
    budget: "NarrativeBudget"
```

`NarrativeBudget` (conceptual):
```python
@dataclass
class NarrativeBudget:
    max_tokens: int
    max_ms: int
    allow_external_calls: bool
```

---

### 6.2 NarrativeEngineInterface (`narrative/interface.py`)
Runtime interacts only with this interface:
```python
class NarrativeEngineInterface:
    def run_tick_jobs(self, ctx: NarrativeTickContext) -> NarrativeTickOutput: ...
    def summarize_episode(self, ctx: NarrativeEpisodeContext) -> "NarrativeEpisodeOutput": ...
    def describe_scene(self, ctx: NarrativeUICallContext) -> "NarrativeUIText": ...
```

Implementation rules:
* Uses `adapters.py` to:
  * build LLM prompts from `ctx`,
  * parse outputs into `SubstrateSuggestion`, `StoryFragment`, `MemoryUpdate`.
* Respects `policy.py` (budgets, safety).
* Can internally queue jobs, but all visible outputs must be returned via these methods.

---

## 7. Safety, Budget & Policy (`narrative/policy.py`)
Narrative is **non-deterministic** by nature (LLM), but the engine must constrain its impact.

---

### 7.1 Safety Rules
* No narrative job may:
  * request arbitrary network access outside configured LLM/memory services,
  * read or write files outside its sandbox (if applicable),
  * generate commands outside allowed `SubstrateSuggestion` kinds.
* All SubstrateSuggestion outputs are **validated** by runtime before being turned into ECS commands:
  * invalid `agent_id` → drop and optionally emit a diagnostic event,
  * unknown `intent_code` / `reason_code` → drop or map to safe default.

---

### 7.2 Budget & Throttling
* `NarrativeBudget` is supplied by runtime per call:
  * controls max tokens/latency,
  * can disable narrative entirely for low-power or deterministic testing modes.
* Policy can:
  * skip tick-level narrative jobs except every N ticks,
  * cap the number of agents receiving `PrimitiveIntent` per tick.

---

## 8. Determinism, Replay & Logging
### 8.1 Deterministic Substrate vs Non-Deterministic Narrative
The numeric **substrate** (ECS + world) is deterministic **given** a fixed sequence of:
* external player inputs,
* **narrative outputs** (treated as exogenous inputs),
* RNG seeds (per SOP-200).

Narrative itself may be non-deterministic, but we can achieve replay by:
* logging all `SubstrateSuggestion` outputs per tick, plus:
  * tick index,
  * agent IDs,
  * intent payloads.

During replay:
* runtime can **bypass narrative calls** and re-inject the logged `SubstrateSuggestions`.

---

### 8.2 Trace Logging (`narrative/trace.py`)
Optional helper module for:
* logging prompts and responses (subject to privacy constraints),
* logging structured outputs (SubstrateSuggestion, StoryFragment, MemoryUpdate),
* providing dev tooling for inspecting narrative decisions.

Trace logging must be:
* optional,
* configurable by environment (dev vs prod),
* free of engine-layer imports.

---

## 9. Layer Mapping (SOP-300: L6/L7)
Per **SOP-300** and **SOT-SIM4-ECS-SUBSTRATE-COMPONENTS**:
* L1–L5 are numeric/structural **substrate** and live in ECS components.
* L6–L7 (Reflection & Narrative/Persona) live in:
  * `narrative/` (semantic logic),
  * external semantic memory stores (referenced via IDs in `NarrativeState`).

This SOT enforces:
* Narrative can **read**:
  * numeric substrates (via `AgentSnapshot`),
  * `NarrativeState` fields,
  * world & event snapshots.
* Narrative can **write** only:
  * numeric fields of `NarrativeState` (via `NarrativeStateUpdate` suggestions),
  * `PrimitiveIntent` (int-coded motives/intents, not text),
  * external semantic memory (through `MemoryUpdate` → `memory_store.py`).

Narrative never stores free-text **inside** ECS substrate; all text lives in:
* narrative trace/memory,
* snapshot/episode structures,
* UI-level data.

---

## 10. Extension Rules (Sim5+)
Sim5 or later may extend narrative interface by:
* Adding new `SubstrateSuggestion.kind` values (e.g. “DriveNudge”, “EmotionNudge”) iff:
  * they remain purely numeric,
  * they are gated via runtime policies,
  * they are documented in this SOT and in ECS-related SOTs.
* Adding new job types (e.g., `CharacterArcPlannerJob`) with explicit:
  * inputs (context schemas),
  * outputs (structured suggestions only).

It must **not**:
* allow narrative to issue arbitrary ECS commands,
* bypass `PrimitiveIntent` and `NarrativeState` as the main substrate touchpoints,
* introduce cross-imports from `narrative/` into engine core beyond the adapter interface.

---

## 11. Completion Conditions for SOT-SIM4-NARRATIVE-INTERFACE
This SOT is considered implemented and respected when:
1. `narrative/` folder exists with at least:
  * `interface.py`,
  * `jobs.py`,
  * `adapters.py`,
  * `policy.py`,
  * `memory_store.py` (even if stubbed),
  * `trace.py` (optional but recommended).
2. `NarrativeEngineInterface`:
   * exposes `run_tick_jobs`, `summarize_episode`, `describe_scene`,
   * is the **only** narrative entry point used by runtime.
3. `NarrativeTickContext`, `NarrativeTickOutput`, `SubstrateSuggestion`, `StoryFragment`, and `MemoryUpdate`:
   * are defined as plain, Rust-portable data types,
   * are used consistently across runtime and narrative layers.
4. Runtime:
   * calls `run_tick_jobs()` only in Phase I (post-diff),
   * translates `SubstrateSuggestion` outputs into:
     * ECS commands targeting `PrimitiveIntent` and `NarrativeState`,
     * queued for **next tick’s Phase A**,
     * never lets narrative directly mutate ECS or world.
5. Narrative:
   * reads only via the input schemas (snapshots, events, agent snapshots, budgets),
   * writes only via structured outputs (no direct engine handles),
   * stores all free-text in narrative/memory/snapshot layers, not in ECS.
6. There are no imports from:
   * `ecs/`, `world/`, `snapshot/`, or `integration/` into `narrative/`,
   * except through the agreed DTO schemas defined in runtime/adapters.

At that point, the **Narrative Interface** is:
* **Sim4-correct** as a safe, sidecar semantic layer,
* fully compatible with the numeric substrate & Free Agent Spec,
* and ready for Junie-style implementation sprints without ambiguity about responsibilities or boundaries.