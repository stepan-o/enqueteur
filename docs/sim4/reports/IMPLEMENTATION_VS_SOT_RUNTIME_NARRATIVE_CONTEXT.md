### SIM4 — Implementation Review vs SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT

Date: 2026-02-07

Scope of this report
- Assess current implementation vs docs/sim4/SOTs/SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT.md.
- Focus on runtime-owned DTOs, the narrative bridge entrypoint, logging surfaces, and export wiring.

References
- SOT: docs/sim4/SOTs/SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT.md
- Runtime bridge + DTOs: backend/sim4/runtime/narrative_context.py
- Export overlays (optional): backend/sim4/integration/export_overlays.py

---

Summary of Findings
- Runtime owns the narrative DTOs and the NarrativeRuntimeContext entrypoint (✅).
- Narrative execution is gated and failure-safe (✅).
- History logging is limited to record_narrative_tick_output via HistoryBuffer interface (✅).
- BubbleEvents/UI overlay pipeline is **not implemented** (❌).
- Export/replay surfaces for narrative outputs are not wired (❌).

---

Detailed Conformance Matrix

1) Runtime owns and uses the DTOs (SOT §4)
- Implemented in backend/sim4/runtime/narrative_context.py:
  - NarrativeBudget, NarrativeTickContext, NarrativeTickOutput
  - SubstrateSuggestion, StoryFragment, MemoryUpdate
  - NarrativeEpisodeContext/Output and UI call DTOs
  - NarrativeEngineInterface and HistoryBuffer Protocols
- Assessment: ✅ Compliant. DTOs are dataclasses, primitives‑only or composed of snapshot DTOs.

2) Single tick‑level entrypoint (NarrativeRuntimeContext)
- Implemented: NarrativeRuntimeContext with build_tick_context(...) and run_tick_narrative(...).
- run_tick_narrative:
  - Honors enable flag and tick stride (policy gating).
  - Builds a read‑only WorldSnapshot from snapshot layer.
  - Calls NarrativeEngineInterface.run_tick_jobs(ctx) inside try/except.
  - Logs outputs best‑effort to history.
- Assessment: ✅ Compliant. One clear entrypoint; no ECS/world mutation.

3) Phase and failure modes (SOT §6, §10)
- Phase: Narrative runs after snapshot building; no world/ECS mutations.
- Failure handling: Exceptions are swallowed; output falls back to empty NarrativeTickOutput.
- Assessment: ✅ Compliant with robustness requirements.

4) History logging surfaces (SOT §7)
- HistoryBuffer Protocol includes:
  - get_diff_summary_for_tick(...)
  - record_narrative_tick_output(...)
- NarrativeRuntimeContext calls record_narrative_tick_output(...) in best‑effort mode.
- Assessment: ✅ Compliant for the implemented subset. No bubble event logging exists.

5) BubbleEvents pipeline (SOT §7.2–§7.3)
- Not implemented.
- Removed modules: runtime/bubble_bridge.py and integration/ui_events.py.
- Assessment: ❌ Not compliant with the bubble export portion of the SOT.

6) Export and replay surfaces (SOT §7.3, §9)
- No narrative export wiring exists in current code.
- Overlays can be written by integration if supplied externally (export_overlays.py),
  but runtime does not generate or map StoryFragments into overlays.
- Assessment: ❌ Not implemented.

7) Guardrails: SOP‑100/200 and coupling
- No clocks/RNG in narrative mapping.
- Integration does not import runtime.
- DTOs are primitives‑only and Rust‑portable.
- Assessment: ✅ Compliant.

---

Gaps, Deferrals, and Notes
- recent_events: NarrativeTickContext.recent_events remains empty; wiring is deferred.
- SubstrateSuggestion application: still planned; no ECS mutation.
- BubbleEvents/UI overlays: not wired; any overlays must be provided out‑of‑band to integration.

Risks & Considerations
- Without UI export wiring, viewers cannot consume narrative outputs directly.
- HistoryBuffer implementation is not provided in this repo; logging correctness depends on callers.

Recommendations
- If UI overlays are needed, define a StoryFragment → overlay mapping in a dedicated, deterministic module.
- Add a concrete HistoryBuffer implementation or test harness to validate narrative logging.
- Clarify in the SOT whether bubble export is a hard requirement or a separate optional pipeline.

Conclusion
The current implementation meets the core runtime ↔ narrative DTO and bridge requirements,
but **does not** implement bubble events or narrative export wiring. The SOT should be
treated as partially implemented until those pipelines exist.
