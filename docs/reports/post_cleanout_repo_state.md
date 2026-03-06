# 1. Executive Summary
Yes, this is now a strong technical base for Enquêteur, but not yet a gameplay-ready MBAM implementation.

What is solid now:
- Deterministic tick/runtime spine, world state substrate, snapshot/diff/export/replay pipeline, and a capable Pixi viewer shell are all in place.
- Backend test baseline is green (`uv run --extra dev -m pytest backend/sim4/tests -q` passed).

Biggest missing layers:
- No deterministic MBAM case-truth engine (`CaseState`, role assignment, clue/evidence graph, timeline beats).
- No investigation interaction model (object affordances/state transitions, evidence workflow, accusation/win/fail logic).
- No dialogue adapter implementation (LLM contract is scaffold-level only).
- No French-learning scaffolding/minigame implementation.

Top risks:
- Core ECS/system stack is still heavily scaffold/skeleton.
- Legacy workstation/economy semantics are still the only substantive “gameplay” logic.
- Live transport is adapter-level only (no actual WS host runtime wiring in repo).
- Frontend is still primarily a sim viewer/dev console, not investigation UX.

# 2. Repo State Overview
High-value current modules:

- `backend/sim4/ecs`: ECS substrate, components, scheduler ordering, and systems.
- `backend/sim4/world`: world model, world commands/events, MBAM layout, static map generation.
- `backend/sim4/runtime`: deterministic tick orchestration and command/event consolidation.
- `backend/sim4/snapshot`: world snapshot builder, snapshot diff, episode scaffolding.
- `backend/sim4/integration`: KVP envelopes, canonicalization, state diff ops, manifest/export/verify, live session abstractions.
- `backend/sim4/host`: orchestrator (`SimRunner`) and default run/render spec builders.
- `scripts`: deterministic-ish demo/export scripts.
- `frontend/enqueteur-webview`: Pixi renderer, KVP live/offline ingestion, dev HUD/controls/inspect panels.
- `docs/enqueteur/case_1_implementation_spec.md`: MBAM source of truth.

# 3. Current Reusable Spine
Concrete reusable foundation to build Enquêteur v1.0 on:

- Deterministic runtime kernel:
  [backend/sim4/runtime/tick.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/tick.py), [backend/sim4/runtime/clock.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/clock.py), [backend/sim4/runtime/command_bus.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/command_bus.py), [backend/sim4/runtime/events.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/events.py)
- World truth substrate + MBAM map:
  [backend/sim4/world/context.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/context.py), [backend/sim4/world/mbam_layout.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/mbam_layout.py), [backend/sim4/world/static_map.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/static_map.py), [backend/sim4/world/apply_world_commands.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/apply_world_commands.py)
- Snapshot/diff/replay-export stack:
  [backend/sim4/snapshot/world_snapshot_builder.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/snapshot/world_snapshot_builder.py), [backend/sim4/integration/export_state.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/integration/export_state.py), [backend/sim4/integration/export_verify.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/integration/export_verify.py), [backend/sim4/integration/manifest_schema.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/integration/manifest_schema.py), [backend/sim4/integration/diff_ops.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/integration/diff_ops.py)
- Host orchestration:
  [backend/sim4/host/sim_runner.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/host/sim_runner.py)
- Frontend world-view shell:
  [frontend/enqueteur-webview/src/app/boot.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/boot.ts), [frontend/enqueteur-webview/src/state/worldStore.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/state/worldStore.ts), [frontend/enqueteur-webview/src/render/pixiScene.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/render/pixiScene.ts), [frontend/enqueteur-webview/src/kvp/offline.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/kvp/offline.ts), [frontend/enqueteur-webview/src/kvp/client.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/kvp/client.ts)

# 4. Backend Implementation Status
World model:
- Implemented: rooms, agents, items, objects, doors, world time/day-phase in [backend/sim4/world/context.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/context.py).
- MBAM layout is concrete and deterministic in [backend/sim4/world/mbam_layout.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/mbam_layout.py).

Ticking/scheduling:
- Deterministic tick pipeline A–I exists in [backend/sim4/runtime/tick.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/tick.py).
- Systems run for phases B/C/D only. Phase E currently applies buffered ECS commands; `PHASE_E_SYSTEMS` is not invoked by runtime tick.
- Per-system deterministic seed derivation exists.

Actions/interactions:
- Working world command application exists (`set_agent_room`, spawn/despawn item, open/close door).
- ECS interaction pipeline is mostly skeleton (intent resolution, movement resolution, interaction resolution, inventory, action execution are TODO scaffolds).
- Substantive active gameplay-like logic is currently workstation/economy-oriented (`WorkDesire`, `WorkAssignment`, object wear/output).

Movement/navigation/pathing:
- No true pathfinding/navigation solver.
- World neighbor graph and door state exist but not deeply enforced in movement systems.
- Agent movement in backend is mostly workstation-target steering.

Determinism/seed handling:
- Strong at kernel level.
- Weak at content/case level (no MBAM role/timeline/evidence seed engine).
- Demo script world seeding is partly non-deterministic because it uses `random.uniform(...)` without explicit `random.seed(...)` in [scripts/run_sim4_kvp_demo.py](/Users/stpn/Documents/repos/my_projects/enqueteur/scripts/run_sim4_kvp_demo.py).

Event logging:
- World events emitted deterministically from world command applier.
- Runtime event envelope exists and consolidates world/ecs/runtime streams.
- ECS-origin runtime events are not yet wired.

Snapshots/diffs:
- Snapshot builder exists and includes rooms/agents/items/objects/doors.
- Large portions of agent semantic state are stubbed in snapshot builder (identity/drives/social/plan mostly empty placeholders).
- KVP diff pipeline (ops-based), hash chain, manifest/integrity, and replay verification are mature.

MBAM integration:
- Layout and object placement are present.
- MBAM case logic (culprit assignment, clue graph, timeline beats, evidence placement, trust/stress gates) is absent.

Strengths:
- Deterministic orchestration and data projection are real and reusable.
- Export/verify/replay infrastructure is unusually strong for current stage.

Limitations:
- Investigation gameplay logic layer is effectively missing.
- Current non-skeleton systems are domain-draggy (production/workstation semantics).

# 5. Frontend Implementation Status
Rendering model:
- Pixi scene is robust with layered rendering, camera controls, floor filtering, room focus/cutout, object/agent draw passes, overlays, and desync banner in [frontend/enqueteur-webview/src/render/pixiScene.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/render/pixiScene.ts).
- Object visuals are code-defined primitives in [frontend/enqueteur-webview/src/render/objectRegistry.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/render/objectRegistry.ts), good for asset swap later.

State ingestion:
- `WorldStore` supports snapshot+diff ingestion and local desync detection.
- Offline playback loader is feature-rich (manifest, keyframes, seek/speed, overlays).
- Live client has protocol handshake and plugin dispatch.

Controls/debugging:
- Dev controls include floor, camera mode/rotation, playback pause/speed/seek/restart, keyframe marks, highlights.
- HUD, inspect panel, and time-lighting overlays are implemented.

Interaction affordances:
- Reusable inspect/select/focus patterns exist.
- No gameplay actions from inspect state into backend commands yet (viewer-only interactions).

Replay/viewer capabilities:
- Strong offline replay UX hooks already exist.
- Overlay streams (`X_UI_EVENT_BATCH`, `X_PSYCHO_FRAME`) are consumable and shown.

What is reusable for gameplay:
- Selection/highlight/focus behaviors, timeline controls, overlay event channeling, and dynamic scene composition are immediately useful.

What is viewer/dev-only:
- Most UI is debug-oriented.
- No dialogue shell, clue board, notebook, inventory/evidence interaction UX, accusation flow, or learning scaffolding UI.

# 6. Schema / Session / Transport Status
What exists:
- SSoT constants for protocol/schema versions.
- Strict envelope validators for artifact and live transport.
- Manifest schema + validation + integrity mapping.
- Canonicalization + deterministic hash chain.
- Snapshot/diff export + replay reconstruction verifier.
- Live session state machine abstraction and live sink adapter.

Maturity assessment:
- Offline artifact contract is mature and test-backed.
- Frontend/backend coupling via `engine_name`/`schema_version` plugin routing is good.
- Live path is partial: protocol/session helpers exist, but no complete repo-local WS server/runtime host integration path is present.
- Frontend does not strongly schema-validate payload internals beyond basic shape checks.

# 7. MBAM Spec Coverage Check
| MBAM area | Status | Evidence in code | Assessment |
|---|---|---|---|
| Room layout (Lobby/Gallery/Security/Corridor/Café + doors) | Implemented now | [backend/sim4/world/mbam_layout.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/mbam_layout.py) | Solid for spatial foundation. |
| Object placement (core props) | Partially supported / scaffold exists | [backend/sim4/world/mbam_layout.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/mbam_layout.py), [frontend/enqueteur-webview/src/render/objectRegistry.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/render/objectRegistry.ts) | Spatial objects exist; affordance/state logic does not. |
| Object affordances and object state machines (`inspect`, `check_lock`, etc.) | Missing but natural insertion point exists | [backend/sim4/world/context.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/context.py), [backend/sim4/world/commands.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/commands.py) | Add object-instance state + commands + UI action binding. |
| Fixed cast (Élodie/Marc/Samira/Laurent/Jo) | Missing | N/A | No cast registry/data layer yet. |
| Seeded role assignment (culprit/ally/misdirect/method/drop) | Missing but natural insertion point exists | [backend/sim4/runtime/tick.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/tick.py), [backend/sim4/host/sim_runner.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/host/sim_runner.py) | Need deterministic CaseState generator layer. |
| Timeline beats and pressure windows | Partially supported / scaffold exists | [backend/sim4/runtime/clock.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/clock.py), [scripts/run_sim4_kvp_demo.py](/Users/stpn/Documents/repos/my_projects/enqueteur/scripts/run_sim4_kvp_demo.py) | Tick clock and scheduled commands exist; MBAM beat logic absent. |
| Evidence/clue graph | Missing but natural insertion point exists | [backend/sim4/snapshot/world_snapshot.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/snapshot/world_snapshot.py) | No clue/evidence truth graph model today. |
| Dialogue scene structure + gating | Missing but natural insertion point exists | [backend/sim4/runtime/narrative_context.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/narrative_context.py), [backend/sim4/narrative/interface.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/narrative/interface.py) | DTO bridge exists; logic is stubbed/null engine. |
| Trust/stress/state cards | Partially supported / scaffold exists | [backend/sim4/ecs/components/social.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/ecs/components/social.py), [backend/sim4/ecs/components/emotion.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/ecs/components/emotion.py), [frontend/enqueteur-webview/src/ui/hud.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/ui/hud.ts) | Data substrate exists but no MBAM semantics/wiring. |
| French scaffolding ladder | Missing | N/A | No language pedagogy contract implemented. |
| Minigames MG1–MG4 | Missing | N/A | No backend evaluators or frontend minigame flows. |
| Win/fail/best ending conditions | Missing | N/A | No case resolution engine exists. |
| Replayability/seeds | Partially supported / scaffold exists | [backend/sim4/runtime/tick.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/tick.py), [backend/sim4/integration/export_verify.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/integration/export_verify.py) | Runtime replay is strong; MBAM seed semantics absent. |
| LLM truth-guard (“LLM never invents facts”) | Risky / unclear | [backend/sim4/runtime/narrative_context.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/narrative_context.py) | No implemented allowed-facts enforcement loop yet. |

# 8. Architecture Gaps
Major missing implementation layers for Enquêteur v1.0:

- Deterministic `CaseState` engine for MBAM (`seed -> roles/timeline/evidence/alibi/truth_graph/outcomes`).
- Canonical NPC cast/identity layer with recurring characters and per-run role overlays.
- Object affordance/state system (interaction verbs, prerequisite checks, state transitions, evidence spawning).
- Player action command model (input commands, validation, deterministic application, accept/reject responses).
- NPC knowledge/trust/stress/alibi model wired into runtime state transitions.
- Dialogue adapter contract implementation with strict allowed-facts slices and trust/stress deltas.
- Clue graph + contradiction engine.
- Investigation UI shell (notebook, clue board, evidence inventory, timeline/alibi view, accusation flow).
- French scaffolding and minigame subsystem with deterministic grading/gating.
- Resolution/progression layer (win/fail/best ending + seed-driven replay loops).

# 9. Hidden Couplings / Technical Debt / Leftover Assumptions
Important inherited debt likely to cause drag:

- Workstation/economy semantics are deeply threaded through object catalog, ECS systems, snapshots, and renderer assumptions:
  [backend/sim4/world/object_catalog.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/object_catalog.py), [backend/sim4/ecs/systems/object_workstation_system.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/ecs/systems/object_workstation_system.py), [backend/sim4/ecs/components/agent_stats.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/ecs/components/agent_stats.py)
- Runtime tick never executes `PHASE_E_SYSTEMS` even though scheduler defines them.
- Snapshot builder emits many stubbed semantic fields, which can falsely suggest “implemented semantics.”
- Frontend live mode has weaker schema guarantees and no full server/runtime path in-repo.
- Demo-run script uses unseeded Python `random` during world build, undermining strict reproducibility.
- Some viewer heuristics still encode old semantic labels (`supervisor`, etc.) in room layout fallback logic:
  [frontend/enqueteur-webview/src/render/pixiScene.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/render/pixiScene.ts)
- No frontend test suite currently present.
- Frontend build was not executable in current environment without installing TS toolchain (`tsc` missing).

# 10. Strong Opportunities / Low-Hanging Extensions
Leverage points that are better than expected:

- Replay/export stack already enforces canonicalization and hash-chain integrity; ideal for case-debug/replay tooling.
- Overlay channels are already pipeline-ready for clue highlights, dialogue cues, and tutorial nudges.
- Pixi scene already supports inspect/focus/select and camera scripting, which maps well to investigation gameplay.
- Narrative DTO bridge is a good foundation for “LLM adapter only” architecture.
- Static map + object placement data can quickly support deterministic reachability and interaction-range checks.
- Plugin registry by `engine_name/schema_version` gives forward-compatible transport evolution room.

# 11. Enquêteur v1.0 Implementation Plan
1. **Phase 1: Canonical Case-State Layer**  
   Goals: deterministic MBAM truth model per seed.  
   Backend changes: add `CaseState` types and seed generator; include role assignment, timeline schedule, evidence placement, alibi matrix, truth graph.  
   Frontend changes: none required initially except debug readout panel hooks.  
   Data/schema changes: add case payload slice to snapshot/export (`case_id`, `seed`, `truth_epoch`, minimal case visibility subset).  
   Testing/validation: same-seed identity tests, cross-seed variation tests, golden fixture for seeds A/B/C.  
   Dependencies: existing runtime tick + snapshot/export stack.  
   Risk notes: avoid coupling case truth to renderer/world projection.

2. **Phase 2: Object Investigation Interaction Loop**  
   Goals: make MBAM objects interactable with deterministic outcomes.  
   Backend changes: object-instance state store and commands (`inspect`, `check_lock`, `read`, `request_access`, etc.); evidence spawn/linking.  
   Frontend changes: inspect panel action tray and result cards; object highlight feedback.  
   Data/schema changes: extend diff ops and payloads for object-state/evidence updates and command acks.  
   Testing/validation: command determinism, illegal-action rejection, object-state transition tests.  
   Dependencies: Phase 1 case truth rules.  
   Risk notes: keep object affordance logic case-data-driven, not hardcoded in scene code.

3. **Phase 3: NPC Truth/Trust/Timeline Substrate**  
   Goals: implement cast states and timeline-dependent NPC behavior.  
   Backend changes: `NPCState` model (trust, stress, stance, knowledge flags, alibi claims), deterministic beat scheduler, fact reveal gating.  
   Frontend changes: NPC state cards and interaction context hints.  
   Data/schema changes: snapshot/diff support for NPC state deltas and timeline beat markers.  
   Testing/validation: deterministic trust/stress deltas, timeline beat reproducibility, contradiction checks.  
   Dependencies: Phase 1 case truth + Phase 2 interaction events.  
   Risk notes: prevent drift between case truth graph and NPC-exposed facts.

4. **Phase 4: Dialogue Adapter Contract + Investigation Shell**  
   Goals: enforce “LLM adapts dialogue only, never truth.”  
   Backend changes: implement narrative adapter using allowed-facts slices, intent parse contracts, trust/stress updates, refusal/retry logic.  
   Frontend changes: dialogue panel, intent feedback, fact summary confirmation UI.  
   Data/schema changes: define structured dialogue turn envelopes and scene state transitions.  
   Testing/validation: adversarial tests for fact leakage, contract schema tests, deterministic transcript replay tests.  
   Dependencies: Phase 3 NPC state model.  
   Risk notes: strict guardrails required before any production LLM wiring.

5. **Phase 5: French Scaffolding + Minigames**  
   Goals: deliver A1–A2 learning loop integrated with investigation progress.  
   Backend changes: deterministic evaluators for MG1–MG4 and scaffolding ladder policy engine.  
   Frontend changes: minigame widgets, hint tiers, sentence-stem interactions, retry UX.  
   Data/schema changes: add learning-state fields and per-turn scaffolding metadata.  
   Testing/validation: scoring correctness, progression gating, difficulty profile behavior.  
   Dependencies: Phase 4 dialogue and interaction surfaces.  
   Risk notes: ensure pedagogical feedback does not bypass required French actions.

6. **Phase 6: Outcomes, Replay Productization, Content Completion**  
   Goals: complete MBAM end-state logic and replay loop.  
   Backend changes: win/fail/best-ending evaluator, soft-fail carryover hooks, run summary emitter.  
   Frontend changes: resolution screens, evidence recap timeline, replay seed selector.  
   Data/schema changes: outcome summary records and episode recap payloads.  
   Testing/validation: end-to-end seed replay parity, branch coverage for all endings, offline artifact verification.  
   Dependencies: Phases 1–5.  
   Risk notes: keep outcome evaluation purely deterministic and evidence-backed.

# 12. Recommended Immediate Next Steps
1. Add a new backend `CaseState` module and deterministic MBAM seed generator (A/B/C) with tests first.
2. Add a backend `NPCState` datamodel and cast registry for the five fixed characters.
3. Add object-instance MBAM state fields and affordance command handlers for O1–O10.
4. Define and implement a minimal player command contract (`SIM_INPUT` -> validated world/case command).
5. Extend snapshot/export payloads with a minimal case slice and NPC slice.
6. Implement a first contradiction/evidence graph service and connect it to object interactions.
7. Implement a strict dialogue adapter interface with `allowed_facts` gating and refusal behavior.
8. Upgrade inspect panel into an interaction panel (actions + evidence results + hint tier).
9. Add a clue board/timeline UI that visualizes facts, contradictions, and unresolved questions.
10. Create end-to-end deterministic tests for one MBAM seed through accusation resolution.

# 13. Appendix: File-Level Pointers
- [docs/enqueteur/case_1_implementation_spec.md](/Users/stpn/Documents/repos/my_projects/enqueteur/docs/enqueteur/case_1_implementation_spec.md) - Locked MBAM source-of-truth spec.
- [backend/sim4/runtime/tick.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/tick.py) - Core deterministic orchestration path.
- [backend/sim4/runtime/scheduler.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/scheduler.py) - Phase-system ordering integration.
- [backend/sim4/runtime/narrative_context.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/narrative_context.py) - Dialogue/narrative adapter insertion point.
- [backend/sim4/world/context.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/context.py) - Authoritative world substrate.
- [backend/sim4/world/mbam_layout.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/mbam_layout.py) - Current MBAM map and prop placement.
- [backend/sim4/world/apply_world_commands.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/apply_world_commands.py) - World mutation dispatcher/event emission.
- [backend/sim4/world/object_catalog.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/world/object_catalog.py) - Current object behavior tuning (legacy-heavy).
- [backend/sim4/runtime/object_bootstrap.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/runtime/object_bootstrap.py) - Object ECS bootstrap bridge.
- [backend/sim4/snapshot/world_snapshot_builder.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/snapshot/world_snapshot_builder.py) - What state is actually projected.
- [backend/sim4/integration/manifest_schema.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/integration/manifest_schema.py) - Canonical replay manifest contract.
- [backend/sim4/integration/export_state.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/integration/export_state.py) - Snapshot/diff artifact generation.
- [backend/sim4/integration/export_verify.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/integration/export_verify.py) - Replay reconstruction integrity checks.
- [backend/sim4/integration/live_session.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/integration/live_session.py) - Live protocol session state machine abstraction.
- [backend/sim4/host/sim_runner.py](/Users/stpn/Documents/repos/my_projects/enqueteur/backend/sim4/host/sim_runner.py) - End-to-end host orchestration entry point.
- [scripts/run_sim4_kvp_demo.py](/Users/stpn/Documents/repos/my_projects/enqueteur/scripts/run_sim4_kvp_demo.py) - Practical wiring example and current behavior constraints.
- [frontend/enqueteur-webview/src/app/boot.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/app/boot.ts) - Frontend runtime wiring root.
- [frontend/enqueteur-webview/src/state/worldStore.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/state/worldStore.ts) - Frontend authoritative mirrored state + diff application.
- [frontend/enqueteur-webview/src/kvp/offline.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/kvp/offline.ts) - Offline replay loader and scrubber behavior.
- [frontend/enqueteur-webview/src/kvp/client.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/kvp/client.ts) - Live protocol client and plugin dispatch.
- [frontend/enqueteur-webview/src/render/pixiScene.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/render/pixiScene.ts) - Main rendering/interaction shell.
- [frontend/enqueteur-webview/src/ui/devControls.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/ui/devControls.ts) - Existing playback/control scaffolding.
- [frontend/enqueteur-webview/src/ui/inspectPanel.ts](/Users/stpn/Documents/repos/my_projects/enqueteur/frontend/enqueteur-webview/src/ui/inspectPanel.ts) - Natural place to evolve object/NPC interaction UX.