### SIM4 — Implementation Review vs SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT

Date: 2025-12-18

Scope of this report
- Assess the current implementation against the specification in docs/sim4/SOTs/SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT.md.
- Focus on runtime-owned DTOs, the narrative bridge entrypoint, logging/replay surfaces, BubbleEvents pipeline, determinism, and guardrails.
- Provide a clear compliance checklist, gaps, risks, and recommendations.

References
- SOT: docs/sim4/SOTs/SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT.md
- Runtime bridge + DTOs: backend/sim4/runtime/narrative_context.py
- Bubble bridge (StoryFragment → BubbleEvent): backend/sim4/runtime/bubble_bridge.py
- Integration BubbleEvent schema: backend/sim4/integration/ui_events.py
- Integration exporter: backend/sim4/integration/exporter.py

---

Summary of Findings
- Overall, the codebase conforms to the SOT’s intent and acceptance criteria for the Runtime ↔ Narrative boundary.
- Runtime owns DTOs and provides the single entrypoint class (NarrativeRuntimeContext). Narrative execution is gated and robust to failures.
- Narrative outputs are logged to history best‑effort. BubbleEvents are deterministically produced from StoryFragments at the runtime→integration boundary and exported as ui_events.jsonl by the exporter.
- Determinism and layer boundaries (SOP‑100/200) are upheld: no clocks/RNG in transforms, primitives‑only DTOs, and integration does not import runtime.
- Known deferrals are honored: recent_events plumbing and substrate suggestion application are intentionally deferred per the SOT.

---

Detailed Conformance Matrix

1) Runtime owns and uses the DTOs (SOT §4, Completion Criteria §11)
- Implemented in backend/sim4/runtime/narrative_context.py:
  - NarrativeBudget, NarrativeTickContext, NarrativeTickOutput
  - SubstrateSuggestion, StoryFragment, MemoryUpdate
  - NarrativeEpisodeContext/Output and UI call DTOs
  - NarrativeEngineInterface and HistoryBuffer Protocols
- Assessment: Compliant. DTOs are dataclasses, primitives‑only or composed of snapshot DTOs, and Rust‑portable.

2) Single tick‑level entrypoint (NarrativeRuntimeContext) (SOT §5/§6, Criteria §11)
- Implemented: NarrativeRuntimeContext with build_tick_context(...) and run_tick_narrative(...).
- run_tick_narrative:
  - Honors enable flag and tick stride (policy gating).
  - Builds a read‑only WorldSnapshot from snapshot layer.
  - Calls NarrativeEngineInterface.run_tick_jobs(ctx) inside try/except.
  - Logs outputs best‑effort to history.
- Assessment: Compliant. One clear entrypoint; no ECS/world mutation; adheres to SOT.

3) Phase and failure modes (SOT §6, §10, Criteria §11)
- Phase: Narrative runs after history diff summary is retrieved, with no world/ECS mutations (Phase I bridging intent).
- Failure handling: Exceptions from engine execution or history logging are swallowed; output falls back to an empty NarrativeTickOutput.
- Assessment: Compliant with robustness requirements. No time‑based behavior.

4) History logging surfaces (SOT §7)
- HistoryBuffer Protocol includes:
  - get_diff_summary_for_tick(...)
  - record_narrative_tick_output(...)
  - record_bubble_events(...)
- NarrativeRuntimeContext calls record_narrative_tick_output(...) and record_bubble_events(...) in best‑effort mode.
- Assessment: Compliant. Log shapes are explicit and Rust‑portable.

5) BubbleEvents pipeline (SOT §7.2–§7.3, Appendix A)
- Integration schema: backend/sim4/integration/ui_events.py
  - BubbleKind stable string enum: DIALOGUE, THOUGHT, NARRATION.
  - BubbleEvent DTO (primitives‑only) with validation.
  - Deterministic sort key bubble_event_sort_key per policy.
- Runtime mapping: backend/sim4/runtime/bubble_bridge.py
  - Filters whitespace‑only texts.
  - scope → kind mapping: agent→DIALOGUE; room/global/tick/other→NARRATION (deterministic default).
  - Anchoring: agent events carry agent_id+room_id; room narration anchors to room_id only; global is unanchored.
  - importance: round(float) → int, clamped to [-100, 100].
  - duration_ticks from deterministic default (≥1).
  - Returns BubbleEvents sorted by bubble_event_sort_key.
- Exporter writes ui_events/ui_events.jsonl and registers artifact path in RunManifest.artifacts.
- Assessment: Compliant. Deterministic and viewer‑ready per SOT.

6) Export and replay surfaces (SOT §7.3, §9)
- export_run: frames.jsonl (+ events.jsonl optional) and ui_events.jsonl optional; deterministic order enforced for UI events.
- export_replay: keyframes + diffs + index.json; optional ui_events.jsonl included; all writes stable with sorted outputs.
- Assessment: Compliant. Enables viewer scrubbing and narrative replay without rerunning narrative.

7) Guardrails: SOP‑100/200 and coupling
- No clocks/RNG in mapping/exporter.
- Integration layer does not import runtime; exporter only uses integration schemas/utilities. Runtime bridge imports integration DTOs at the boundary (allowed per SOT intent).
- All DTOs are primitives‑only and Rust‑portable; JSON serialization uses stable helpers.
- Assessment: Compliant.

---

Gaps, Deferrals, and Notes
- recent_events: NarrativeTickContext.recent_events is currently an empty list with a “deferred” comment. This matches SOT §8 and is an acknowledged deferral, not a violation.
- SubstrateSuggestion application: SOT marks the substrate application pipeline as “planned” (not implemented). Code aligns with this; no direct ECS mutation is attempted.
- SOT document semantic warnings: The SOT markdown references Python names in prose blocks (e.g., dataclass, WorldSnapshot) that static analyzers may flag as unresolved. This is documentation‑only and does not affect runtime code correctness.
- Thought vs Dialogue: In absence of an explicit marker in StoryFragment to distinguish THOUGHT from DIALOGUE, mapping defaults agent scope to DIALOGUE. If a future marker becomes available, bridge policy can be extended without breaking the current contract (enum values are stable).

Risks & Considerations
- Importance conversion policy: round() + clamp ensures determinism, but upstream expectations should be documented alongside UI behavior (e.g., how viewers resolve ties). The current policy is encoded in code and tests; it should be mirrored in narrative guidelines.
- History implementation coverage: Protocol is defined, calls are made best‑effort, but correctness depends on the concrete HistoryBuffer implementation ensuring durable, deterministic storage of BubbleEvents.
- Replay completeness: ui_events.jsonl is exported; ensuring alignment between tick ranges in frames vs. UI events (e.g., out‑of‑range bubbles) is a caller concern. Exporter currently sorts and writes what it receives.

Recommendations
- Document Thought vs Dialogue marker in StoryFragment once available; extend mapping to use THOUGHT explicitly without changing existing enum values.
- Add a brief note to SOT §7.2 clarifying the chosen importance conversion policy (float → int) to guarantee cross‑language parity.
- When wiring recent_events, maintain SOP‑200 by quantizing any time fields and ensuring stable ordering.
- Consider adding lightweight schema validation for HistoryBuffer storage shapes in tests to ensure BubbleEvents remain primitives‑only and ordered.

Conclusion
The current implementation is aligned with SOT-SIM4-RUNTIME-NARRATIVE-CONTEXT. It satisfies the completion criteria for the narrative bridge and BubbleEvents export, maintains determinism and layer boundaries, and respects the explicitly deferred areas. The identified follow‑ups focus on clarifying minor policies (importance conversion, thought marker) and completing deferred wiring without compromising determinism.
