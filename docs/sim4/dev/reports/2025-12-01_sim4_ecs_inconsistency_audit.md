Sim4 ECS Inconsistency & Compliance Audit

Author: Junie (Sim4 implementation assistant)
Date: 2025-12-01 10:10 (local)

Scope
- Compare the current backend/sim4/ecs/, backend/sim4/ecs/components/, and backend/sim4/ecs/systems/ structure and implementation details against the SOTs:
  - docs/sim4/SOTs/SOT-SIM4-ECS-CORE.md
  - docs/sim4/SOTs/SOT-SIM4-ECS-SUBSTRATE-COMPONENTS.md (+ DETAILS doc)
  - docs/sim4/SOTs/SOT-SIM4-ECS-SYSTEMS.md
  - docs/sim4/SOTs/SOT-SIM4-ECS-COMMANDS-AND-EVENTS.md

Method
- Static inspection of the ECS code and SOTs. No code changes have been made (per instruction). Tests currently pass (pytest -q), so observations focus on spec alignment and potential future risks rather than failing behavior.

High-Level Summary
- Overall the ECS substrate appears largely aligned with SOT principles: layer purity, determinism, and Rust-portable DTOs. The command pipeline and system skeletons follow the intended patterns.
- Notable gaps/inconsistencies are mostly minor and documentation-oriented, with a few areas to clarify with the Architect for future sprints.

Findings by Area

1) Folder Structure & Layer Purity (SOT-SIM4-ECS-CORE §2, §1)
- Observed structure (selected):
  - backend/sim4/ecs/world.py — ECSWorld core, queries, apply_commands
  - backend/sim4/ecs/commands.py — ECSCommand, ECSCommandKind, helpers
  - backend/sim4/ecs/entity.py, archetype.py, storage.py, query.py — present as per SOT
  - backend/sim4/ecs/components/ — substrate components grouped by domain
  - backend/sim4/ecs/systems/ — system skeletons by phase/responsibility
- Layer purity:
  - Systems import from ecs.world and ecs.components.*, which is allowed (SOT says systems see ECSWorld APIs and component types). No systems import runtime, snapshot, world (external), narrative, or integration.
  - ecs/ modules themselves do not import from runtime/, world/, snapshot/, narrative/, or integration/. This is compliant with the DAG.
- Conclusion: Structure and imports align with SOT; no violations found.

2) Determinism Guarantees (SOP-200; SOT-SIM4-ECS-CORE §§ determinism, queries; SOT-SIM4-ECS-SYSTEMS)
- ECSCommandBuffer (backend/sim4/ecs/systems/base.py):
  - Monotonic seq assignment starting from 0; commands property returns a defensive copy. This supports deterministic ordering.
  - Minor typing style nit: create_entity signature uses Optional[List[object]] | None in the current file, which is redundant (Optional already includes None). Not a functional issue, but a consistency nit for code readability and cross-language examples.
  - The buffer’s seq counter is per-buffer. If multiple system buffers are merged at runtime, the runtime must preserve global ordering (SOT: runtime owns sequencing). Current code does not demonstrate cross-buffer merge semantics. This is expected, but worth documenting in runtime SOT alignment.
- ECSWorld.apply_commands (backend/sim4/ecs/world.py):
  - Sorts by cmd.seq before dispatch. This enforces deterministic application given a consistent seq ordering.
  - Strict checks in _apply_set_field (entity existence, component presence, field hasattr) align with early failure for determinism.
- Queries:
  - QueryResult ordering is asserted deterministic by tests; query API is used in system skeletons in a deterministic iteration. The actual query engine implementation wasn’t deeply reviewed here, but tests pass asserting determinism.
- RNG wrapper (SimulationRNG) in systems/base.py follows the SOT guidance for deterministic randomness, seeded externally.
- Conclusion: Determinism is well-treated. The cross-buffer global seq ordering is a runtime concern to confirm later.

3) ECS Commands & Events Alignment (SOT-SIM4-ECS-COMMANDS-AND-EVENTS)
- ECSCommandKind in ecs/commands.py provides stable string values, as required by cross-language contracts.
- The helpers cmd_set_field, cmd_set_component, cmd_add_component, cmd_remove_component, cmd_create_entity, cmd_destroy_entity exist and are used by ECSWorld.apply_commands.
- CREATE_ENTITY payload: The implementation stores the components list in ECSCommand.component_instance (see ecs/commands.py and world._apply_create_entity). SOT allows an “interim compromise” in early sprints; the code explicitly documents this. Alignment: acceptable for now. Later SOT revisions may introduce a distinct payload field to avoid overloading.
- Events and WorldCommand are not implemented in ecs (they belong to world/). Nothing in ecs attempts to emit world events; systems are currently skeletons. This matches SOT layering.
- Conclusion: ECS command side is consistent with SOT. The interim payload overloading is documented; future cleanup likely.

4) Components: Substrate Constraints (SOT-SIM4-ECS-SUBSTRATE-COMPONENTS + DETAILS)
- General:
  - Dataclass use with primitive types, ints/floats/dicts/lists. No free-form text fields observed in substrate components. Rust-portable shapes are followed.
  - Narrative substrate (narrative_state.NarrativeState) marks narrative-owned fields and warns ECS systems to treat as read-only metadata, consistent with SOT.
- Embodiment (backend/sim4/ecs/components/embodiment.py):
  - RoomID/AssetID aliases are ints. Transform/Velocity/RoomPresence/PathState are numeric-only. PathState includes waypoints (List[Tuple[float, float]]) and a progress scalar with comments about range constraints enforced by systems. This matches SOT guidance that components are passive storage.
- Perception (backend/sim4/ecs/components/perception.py):
  - PerceptionSubstrate, AttentionSlots, SalienceState use only numeric IDs and numeric values. Cross-references to EntityID and RoomID/AssetID are appropriate.
- Social (backend/sim4/ecs/components/social.py):
  - SocialSubstrate, SocialImpressionState, FactionAffinityState keep numeric-only fields keyed by IDs. No text labels appear.
- Narrative (backend/sim4/ecs/components/narrative_state.py):
  - Numeric fields only, optional refs by ID. Explicit note that narrative layer mutates via adapters.
- Referenced but not reviewed in this report (exist in repo per imports/tests): identity.py, drives.py, emotion.py, motive_plan.py, inventory.py, intent_action.py, belief.py. System imports reference these; tests for substrates also pass, indicating presence and basic shape compliance.
- Conclusion: Substrate components follow SOT constraints. No free-text fields detected; shapes look Rust-portable.

5) Systems: Responsibilities, Context, and No-IO Skeletons (SOT-SIM4-ECS-SYSTEMS)
- System skeletons present (non-exhaustive):
  - PerceptionSystem, CognitivePreprocessor, DriveUpdateSystem, MovementResolutionSystem, InteractionResolutionSystem, ActionExecutionSystem, PlanResolutionSystem, InventorySystem, EmotionGradientSystem, SocialUpdateSystem, IntentResolverSystem, MotiveFormationSystem, plus scheduler_order and base module.
- base.SystemContext:
  - Contains world (ECSWorld), dt, rng, views (Protocol), commands buffer, tick_index. Matches SOT intent. Note: “world is read-only” is by convention; not enforced by API. This mirrors SOT approach (systems should only mutate via commands).
- base.WorldViewsHandle:
  - Protocol is intentionally a placeholder; SOT mentions views as read-only. No concrete methods specified here yet. This is acceptable for current sprint but should be fleshed out in the world/runtime layer per SOT when needed.
- Skeletons behavior:
  - Each system run(ctx) performs deterministic queries, iterates results, and does not mutate state or issue commands yet. This matches the “skeleton only” scope described in the sprint docs and SOT staging.
- Layer purity:
  - Systems only import from ecs.* (world, components, and base). No forbidden imports.
- Conclusion: Systems align with SOT at skeleton level. Future sprints should implement concrete logic, using ctx.commands and possibly world views, still respecting determinism and layering.

6) API Shape & Typing Consistency Nits
- Optional syntax:
  - In ECSCommandBuffer.create_entity, the annotation Optional[List[object]] | None is redundant; Optional already includes None. This is a stylistic/typing consistency nit; does not affect behavior or SOT.
- Access controls:
  - SystemContext cannot enforce “world read-only,” which is by design in Python. SOT expects discipline rather than language-level enforcement.
- cmd_create_entity payload field overload:
  - Documented as interim. Consider introducing a separate field (e.g., payload or components_list) in a later SOT-aligned refactor for clarity.

7) Tests & Determinism
- The current test suite (backend/sim4/tests) passes; several tests exercise ECSWorld, commands, storage, query determinism, and basic system scaffolding. This supports alignment with SOT intent for early sprints.

Potential Risks / Clarifications for Architect (TODO[ARCH])
- TODO[ARCH]: Cross-buffer sequencing — Confirm runtime mechanism to combine multiple ECSCommandBuffer instances into a single globally-ordered sequence before ECSWorld.apply_commands, ensuring deterministic application across systems.
- TODO[ARCH]: WorldViewsHandle — Define the initial minimal read-only view methods required by Phase B–F systems (e.g., agents_in_room(room_id), room_neighbors(room_id)). Ensure these are implemented in a layer-appropriate module (world/runtime) and passed via SystemContext.
- TODO[ARCH]: CREATE_ENTITY payload overloading — Plan a migration path from using ECSCommand.component_instance to a dedicated payload field (or a dedicated components list field) to avoid semantic overloading while keeping Rust portability.
- TODO[ARCH]: Typing/style unification — Standardize Optional[T] vs T | None usage across the codebase per Python target version and code style guides.
- TODO[ARCH]: Enforce read-only world access in systems via linting or conventions (docstrings/checks), since Python cannot prevent writes to ctx.world. Consider defensive wrappers or policy checks in runtime for development builds.

Conclusion
- The ECS codebase is broadly compliant with the SOTs in structure, determinism, and DTO shapes. The highlighted items are small, mostly documentation or style-level inconsistencies, and a few clarifications to plan for in upcoming sprints. No immediate functional contradictions with the SOTs were found.
