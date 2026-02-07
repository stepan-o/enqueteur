# SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT

**Runtime ↔ Narrative Bridge, Logging/Replay Contracts (No UI Export Wiring Yet)**  
**Draft 1.1** — Architect-level; **SOP-100 / SOP-200 / SOP-300** compliant

---

## 0. Purpose and scope

This SOT defines the **runtime-owned** contracts and orchestrator for Sim4 narrative integration:

- How runtime constructs narrative contexts (**tick / episode / UI**).
- How runtime calls a `NarrativeEngineInterface`.
- How outputs are **validated** and **logged for replay**.
- How outputs may later be applied back into the simulation via **future-tick command scheduling** (planned).

This SOT is the **single source of truth** for how runtime packages data for the narrative sidecar **and** how narrative outputs are recorded to support deterministic replay and viewer playback.

### In scope
- Runtime DTOs:
    - `NarrativeBudget`, `NarrativeTickContext`, `NarrativeTickOutput`
    - `SubstrateSuggestion`, `StoryFragment`, `MemoryUpdate`
    - `NarrativeEpisodeContext`, `NarrativeEpisodeOutput`
    - `NarrativeUICallContext`, `NarrativeUIText`
- Runtime bridge:
    - `NarrativeRuntimeContext` (build contexts, gate stride/budget, call engine, log outputs)
UI/export surfaces are **out of scope** for runtime; any overlays are exported
by integration when supplied by host orchestration.

### Out of scope
- Narrative logic (LLM prompts, semantic reasoning, policy logic) — owned by `narrative/`
- Viewer/UI rendering — owned by integration/viewer SOTs
- ECS/world mutation logic from narrative outputs — **planned** (not implemented in current code)

---

## 1. Status: what is implemented today

### ✅ Implemented (Sprints 8.x)
- Runtime-owned DTOs exist in `runtime/narrative_context.py`.
- `NarrativeRuntimeContext`:
    - Builds `WorldSnapshot` via snapshot builder (read-only).
    - Gets `diff_summary` from History (does not recompute diffs).
    - Applies **budget + stride gating**.
    - Calls `NarrativeEngineInterface.run_tick_jobs`.
    - Logs tick output via `history.record_narrative_tick_output(...)`.
    - Is defensive: engine failures become a **no-op narrative output**.
### ❌ Not implemented (current code)
- **BubbleEvents pipeline** is not present:
  - No `runtime/bubble_bridge.py`
  - No `integration/ui_events.py`
  - No export wiring from narrative outputs to UI overlays

### ⏳ Deferred / planned
- Wiring `recent_events` into `NarrativeTickContext` (currently `[]`).
- Converting `SubstrateSuggestion` into ECS/world commands scheduled for future ticks.
- Episode-level and UI-call narrative lifecycles beyond DTO definitions.

---

## 2. Layering and dependency rules (SOP-100 / SOP-300)

### 2.1 DAG position (authoritative)
```text
Kernel:   runtime → ecs → world
                \         \
                 \         → snapshot → integration (exports)
                  \
                   → narrative (read-only consumer of contexts)

narrative → runtime (outputs only via DTOs + history logs; no direct mutation)
```

---

## 2.2 Allowed imports (SOP-100)
`runtime/narrative_context.py` may import:
    - snapshot DTOs/builders (e.g., `WorldSnapshot`, `AgentSnapshot`, snapshot builder)
    - runtime-owned history protocols
    - world event DTOs (as data only)
    - **MUST NOT import** integration contracts except at an explicit “bridge edge” module (see §7)

`integration/` must not import runtime.  
`ecs/`, `world/`, `snapshot/` must not import runtime narrative bridge.

---

## 3. File layout (canonical)
```text
backend/sim4/runtime/
  narrative_context.py # runtime-owned narrative DTOs + bridge
  tick.py # tick driver calls NarrativeRuntimeContext (Phase I) when provided

  backend/sim4/integration/
  export_overlays.py # optional overlay writers (ui_events/psycho_frames JSONL)
```

---

## 4. Runtime-owned DTOs (inputs + outputs)

---

### 4.1 NarrativeBudget
```py
@dataclass
class NarrativeBudget:
    max_tokens: int
    max_ms: int
    allow_external_calls: bool
    tick_stride: int = 1
```

---

### 4.2 NarrativeTickContext (input to narrative)
```py
@dataclass(frozen=True)
class NarrativeTickContext:
    tick_index: int
    dt: float
    episode_id: int
    world_snapshot: WorldSnapshot
    agent_snapshots: List[AgentSnapshot]
    recent_events: List[WorldEvent]          # currently empty; planned wiring
    diff_summary: Dict[str, object]          # provided by History
    narrative_budget: NarrativeBudget
```

**Key rule:** no ECS/world handles inside contexts — contexts are pure data.

---

### 4.3 NarrativeTickOutput (output from narrative)
```py
@dataclass
class NarrativeTickOutput:
    substrate_suggestions: List[SubstrateSuggestion]
    story_fragments: List[StoryFragment]
    memory_updates: List[MemoryUpdate]
```

---

### 4.4 StoryFragment (runtime shape)
```py
@dataclass(frozen=True)
class StoryFragment:
    scope: str        # "tick" | "agent" | "room" | "global" | ...
    agent_id: int | None
    room_id: int | None
    text: str
    importance: float
```

**Runtime rule:** StoryFragments do not directly mutate ECS/world. They are logged only;
UI overlays, if needed, are exported out-of-band by integration.


---

## 5. History logging contracts (determinism & replay)

### 5.1 HistoryBuffer protocol (current + authoritative)
Runtime depends on history via a protocol:

- `get_diff_summary_for_tick(tick_index, episode_id) -> dict`
- `record_narrative_tick_output(tick_index, episode_id, output) -> None`

History logging must be:
- stable (JSON-serializable)
- deterministic (stable ordering enforced by runtime before logging where applicable)
- sufficient to replay narrative effects without re-calling narrative (where a HistoryBuffer implementation exists)

---

## 6. NarrativeRuntimeContext (bridge orchestrator)

### 6.1 Responsibilities
- Build contexts (tick/episode/UI)
- Apply stride/budget gating
- Call narrative engine interface
- Catch failures and degrade to no-op outputs
- Log outputs to HistoryBuffer

### 6.2 Tick pipeline integration (Phase I)
`runtime.tick(...)` (or tick driver) calls:
- `NarrativeRuntimeContext.run_tick_narrative(...)` exactly once per tick **after snapshot emission**.
- Failures must not affect deterministic kernel execution.

### 6.3 Current implementation note (authoritative)
- `recent_events` is currently `[]` (wiring deferred).
- Only logging is performed; no ECS/world mutations are applied from suggestions yet.

---

## 7. UI overlays (current status)

UI overlays (bubble events, psycho frames, etc.) are **not** produced by runtime.
If overlays are desired for a run, they are supplied to host orchestration and
exported via `integration/export_overlays.py`. There is currently no
`StoryFragment → BubbleEvent` mapping in code.

---

## 8. Planned: SubstrateSuggestion → ECS command scheduling (deferred)

This section is **kept intentionally** as forward design, but is **not implemented** in current code.

### 8.1 Why deferred
Narrative effects on the deterministic substrate must be:
- explicit
- replayable
- applied only via future tick input phases
- constrained to approved substrate components

### 8.2 Future interface (conceptual)
A future `ExternalCommandSink` or runtime command queue may accept validated command DTOs that the tick loop applies in the next tick’s input phase.

**Hard constraint:** narrative must never enqueue arbitrary ECS commands directly.

---

## 9. Replay mode (current intent)

Replay mode means:
- Runtime does **not** call narrative engines.
- Runtime reuses recorded narrative outputs from History logs (if any).
- Viewer exports remain stable and repeatable.

(Exact replay driver is a separate SOT, but this SOT defines the required log shapes.)

---

## 10. Failure modes (must-haves)

If the narrative engine:
- throws,
- times out,
- returns malformed outputs,

runtime must:
- treat as no-op narrative output for that tick,
- log diagnostics if possible,
- never crash the main tick loop.

---

## 11. Completion criteria

This SOT is “implemented” when:
- runtime owns and uses the DTOs in §4
- `NarrativeRuntimeContext` is the only tick-level narrative entry point
- narrative runs only in Phase I (or equivalent post-history phase)
- outputs are logged into history for replay
- no disallowed imports violate SOP-100/SOP-300

---

## Appendix A — Key moments / changes from Draft 1.0 → 1.1

- Focused the SOT on runtime ↔ narrative DTOs and logging.
- Marked UI overlay export as **out of scope** for runtime (handled in integration when provided by host).
- Marked substrate application pipeline as **planned** (not implemented) instead of describing it as present.
