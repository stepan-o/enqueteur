import type {
    FrameDiffPayload as EnqueteurFrameDiffPayload,
    FullSnapshotPayload as EnqueteurFullSnapshotPayload,
    KernelHelloPayload as EnqueteurKernelHelloPayload,
} from "./enqueteurLiveClient";
import type {
    DiffOp,
    FrameDiffPayload,
    FullSnapshotPayload,
    KernelHello,
    KvpCaseOutcomeState,
    KvpCaseRecapState,
    KvpDialogueState,
    KvpEvent,
    KvpInvestigationState,
    KvpLearningState,
    KvpLearningScaffoldingPolicy,
    KvpNpcSemanticState,
    KvpState,
    RunAnchors,
    WorldMeta,
    WorldState,
} from "../../state/worldStore";

export function convertLiveKernelHello(
    payload: EnqueteurKernelHelloPayload
): KernelHello {
    return {
        engine_name: payload.engine_name,
        engine_version: payload.engine_version,
        schema_version: payload.schema_version,
        world_id: payload.world_id,
        run_id: payload.run_id,
        seed: payload.seed,
        tick_rate_hz: payload.tick_rate_hz,
        time_origin_ms: payload.time_origin_ms,
    };
}

export function convertLiveRunAnchors(
    payload: EnqueteurKernelHelloPayload
): RunAnchors {
    return {
        engine_name: payload.engine_name,
        engine_version: payload.engine_version,
        schema_version: payload.schema_version,
        world_id: payload.world_id,
        run_id: payload.run_id,
        seed: payload.seed,
        tick_rate_hz: payload.tick_rate_hz,
        time_origin_ms: payload.time_origin_ms,
    };
}

export function convertLiveFullSnapshot(
    payload: EnqueteurFullSnapshotPayload
): FullSnapshotPayload {
    const state = payload.state ?? {};
    const worldSlice = asRecord(state.world) ?? {};
    const npcsSlice = asRecord(state.npcs) ?? {};
    const investigationSlice = asRecord(state.investigation);
    const dialogueSlice = asRecord(state.dialogue);
    const learningSlice = asRecord(state.learning);
    const resolutionSlice = asRecord(state.resolution) ?? {};

    const dialogue = normalizeDialogueSlice({
        dialogue: dialogueSlice,
        learning: learningSlice,
    });
    const outcome = normalizeOutcomeSlice(asRecord(resolutionSlice.outcome));
    const recap = normalizeRecapSlice(asRecord(resolutionSlice.recap));

    const convertedState: KvpState = {
        rooms: asArray(worldSlice.rooms) as KvpState["rooms"],
        agents: [],
        items: [],
        objects: asArray(worldSlice.objects) as KvpState["objects"],
        world: normalizeWorldMeta(asRecord(worldSlice.clock)),
        events: [],
        npc_semantic: normalizeNpcSemanticSlice(asArray(npcsSlice.npcs)),
        investigation: normalizeInvestigationSlice(investigationSlice) ?? undefined,
        dialogue: dialogue ?? undefined,
        case_outcome: outcome ?? undefined,
        case_recap: recap ?? undefined,
    };

    return {
        schema_version: payload.schema_version,
        tick: payload.tick,
        step_hash: payload.step_hash,
        state: convertedState,
    };
}

export function convertLiveFrameDiff(
    payload: EnqueteurFrameDiffPayload,
    currentState: WorldState
): FrameDiffPayload {
    const ops: DiffOp[] = [];
    let worldMeta = currentState.world ? deepClone(currentState.world) : null;
    let worldMetaChanged = false;
    let npcSemantic = deepClone(currentState.npcSemantic);
    let npcSemanticChanged = false;
    let investigation = currentState.investigation
        ? deepClone(currentState.investigation)
        : null;
    let investigationChanged = false;
    let dialogue = currentState.dialogue ? deepClone(currentState.dialogue) : null;
    let dialogueChanged = false;
    let learning = currentState.dialogue?.learning
        ? deepClone(currentState.dialogue.learning)
        : null;
    let learningChanged = false;
    let caseOutcome = currentState.caseOutcome ? deepClone(currentState.caseOutcome) : null;
    let caseOutcomeChanged = false;
    let caseRecap = currentState.caseRecap ? deepClone(currentState.caseRecap) : null;
    let caseRecapChanged = false;

    for (const rawOp of payload.ops) {
        const op = asRecord(rawOp);
        if (!op) continue;
        const opName = asString(op.op);
        if (!opName) continue;

        switch (opName) {
            case "UPSERT_ROOM": {
                const room = asRecord(op.room);
                if (room) {
                    ops.push({ op: "UPSERT_ROOM", room: room as DiffOpFor<"UPSERT_ROOM">["room"] });
                }
                break;
            }
            case "REMOVE_ROOM": {
                const roomId = asNumber(op.room_id);
                if (roomId !== null) {
                    ops.push({ op: "REMOVE_ROOM", room_id: roomId });
                }
                break;
            }
            case "UPSERT_OBJECT": {
                const object = asRecord(op.object);
                if (object) {
                    ops.push({
                        op: "UPSERT_OBJECT",
                        object: object as DiffOpFor<"UPSERT_OBJECT">["object"],
                    });
                }
                break;
            }
            case "REMOVE_OBJECT": {
                const objectId = asNumber(op.object_id);
                if (objectId !== null) {
                    ops.push({ op: "REMOVE_OBJECT", object_id: objectId });
                }
                break;
            }
            case "SET_CLOCK": {
                worldMeta = normalizeWorldMeta(asRecord(op.clock)) ?? null;
                worldMetaChanged = true;
                break;
            }
            case "UPSERT_NPC": {
                const row = asRecord(op.npc);
                if (!row) break;
                const npcId = asString(row.npc_id);
                if (!npcId) break;
                const next = row as KvpNpcSemanticState;
                npcSemantic = upsertByStringId(npcSemantic, next, "npc_id");
                npcSemanticChanged = true;
                break;
            }
            case "REMOVE_NPC": {
                const npcId = asString(op.npc_id);
                if (!npcId) break;
                npcSemantic = npcSemantic.filter((row) => row.npc_id !== npcId);
                npcSemanticChanged = true;
                break;
            }
            case "REVEAL_EVIDENCE": {
                const evidenceId = asString(op.evidence_id);
                if (!evidenceId) break;
                investigation = ensureInvestigation(investigation);
                investigation.evidence.discovered_ids = appendUniqueSorted(
                    investigation.evidence.discovered_ids,
                    evidenceId
                );
                investigationChanged = true;
                break;
            }
            case "COLLECT_EVIDENCE": {
                const evidenceId = asString(op.evidence_id);
                if (!evidenceId) break;
                investigation = ensureInvestigation(investigation);
                investigation.evidence.collected_ids = appendUniqueSorted(
                    investigation.evidence.collected_ids,
                    evidenceId
                );
                investigationChanged = true;
                break;
            }
            case "SET_OBJECT_INVESTIGATION_STATE": {
                const row = asRecord(op.object_state);
                if (!row) break;
                const objectId = asString(row.object_id);
                if (!objectId) break;
                investigation = ensureInvestigation(investigation);
                investigation.objects = upsertByStringId(
                    investigation.objects,
                    row as KvpInvestigationState["objects"][number],
                    "object_id"
                );
                investigationChanged = true;
                break;
            }
            case "REVEAL_FACT": {
                const factId = asString(op.fact_id);
                if (!factId) break;
                investigation = ensureInvestigation(investigation);
                investigation.facts.known_fact_ids = appendUniqueSorted(
                    investigation.facts.known_fact_ids,
                    factId
                );
                investigationChanged = true;
                break;
            }
            case "MAKE_CONTRADICTION_AVAILABLE": {
                const contradictionId = asString(op.contradiction_id);
                if (!contradictionId) break;
                investigation = ensureInvestigation(investigation);
                investigation.contradictions.unlockable_edge_ids = appendUniqueSorted(
                    investigation.contradictions.unlockable_edge_ids,
                    contradictionId
                );
                investigationChanged = true;
                break;
            }
            case "CLEAR_CONTRADICTION_AVAILABLE": {
                const contradictionId = asString(op.contradiction_id);
                if (!contradictionId) break;
                investigation = ensureInvestigation(investigation);
                investigation.contradictions.unlockable_edge_ids = investigation.contradictions.unlockable_edge_ids
                    .filter((id) => id !== contradictionId);
                investigationChanged = true;
                break;
            }
            case "SET_ACTIVE_SCENE": {
                dialogue = ensureDialogue(dialogue);
                dialogue.active_scene_id = asNullableString(op.scene_id);
                dialogueChanged = true;
                break;
            }
            case "UPSERT_SCENE_STATE": {
                const sceneState = asRecord(op.scene_state);
                if (!sceneState) break;
                const sceneId = asString(sceneState.scene_id);
                if (!sceneId) break;
                dialogue = ensureDialogue(dialogue);
                dialogue.scene_completion = upsertByStringId(
                    dialogue.scene_completion,
                    sceneState as KvpDialogueState["scene_completion"][number],
                    "scene_id"
                );
                dialogueChanged = true;
                break;
            }
            case "APPEND_DIALOGUE_TURN": {
                const turn = asRecord(op.turn);
                if (!turn) break;
                dialogue = ensureDialogue(dialogue);
                const turnIndex = asNumber(turn.turn_index);
                if (turnIndex === null) break;
                const existing = dialogue.recent_turns.some((row) => row.turn_index === turnIndex);
                if (!existing) {
                    dialogue.recent_turns = [...dialogue.recent_turns, turn as KvpDialogueState["recent_turns"][number]]
                        .sort((a, b) => a.turn_index - b.turn_index);
                    dialogueChanged = true;
                }
                break;
            }
            case "SET_HINT_LEVEL": {
                const hintLevel = asString(op.hint_level);
                if (!hintLevel) break;
                dialogue = ensureDialogue(dialogue);
                learning = ensureLearning(learning, dialogue.active_scene_id ?? null);
                learning.current_hint_level = hintLevel;
                learningChanged = true;
                break;
            }
            case "UPSERT_MINIGAME_STATE": {
                const minigameState = asRecord(op.minigame_state);
                if (!minigameState) break;
                const minigameId = asString(minigameState.minigame_id);
                if (!minigameId) break;
                dialogue = ensureDialogue(dialogue);
                learning = ensureLearning(learning, dialogue.active_scene_id ?? null);
                learning.minigames = upsertByStringId(
                    learning.minigames,
                    minigameState as KvpLearningState["minigames"][number],
                    "minigame_id"
                );
                learningChanged = true;
                break;
            }
            case "SET_SUMMARY_STATE": {
                const summaryState = asRecord(op.summary_state);
                if (!summaryState) break;
                dialogue = ensureDialogue(dialogue);
                learning = ensureLearning(learning, dialogue.active_scene_id ?? null);
                learning.summary_by_scene = (
                    asArray(summaryState.summary_by_scene) as KvpLearningState["summary_by_scene"]
                );
                learning.scaffolding_policy = (asRecord(summaryState.scaffolding_policy)
                    ?? learning.scaffolding_policy) as KvpLearningState["scaffolding_policy"];
                learningChanged = true;
                break;
            }
            case "APPEND_LEARNING_OUTCOME": {
                // WorldStore learning shape does not expose recent_outcomes.
                // Keep authoritative progression surfaces (summary/minigame/hint) only.
                break;
            }
            case "SET_RESOLUTION_STATUS": {
                const status = asString(op.status);
                if (!status) break;
                caseOutcome = ensureCaseOutcome(caseOutcome);
                caseOutcome.primary_outcome = status === "in_progress" ? "in_progress" : caseOutcome.primary_outcome;
                caseOutcome.terminal = status !== "in_progress";
                caseOutcomeChanged = true;
                break;
            }
            case "SET_OUTCOME": {
                const outcome = normalizeOutcomeSlice(asRecord(op.outcome));
                caseOutcome = outcome;
                caseOutcomeChanged = true;
                break;
            }
            case "SET_RECAP": {
                const recap = normalizeRecapSlice(asRecord(op.recap));
                caseRecap = recap;
                caseRecapChanged = true;
                break;
            }
            case "APPEND_EVENT": {
                const event = asRecord(op.event);
                if (!event) break;
                const opEvent = toWorldEvent(event, payload.to_tick);
                if (opEvent) {
                    ops.push({
                        op: "UPSERT_EVENT",
                        event: opEvent,
                    });
                }
                break;
            }
            default:
                break;
        }
    }

    if (worldMetaChanged) {
        if (worldMeta) ops.push({ op: "SET_WORLD", world: worldMeta });
        else ops.push({ op: "CLEAR_WORLD" });
    }
    if (npcSemanticChanged) {
        ops.push({ op: "SET_NPC_SEMANTIC", npc_semantic: npcSemantic });
    }
    if (investigationChanged) {
        ops.push({ op: "SET_INVESTIGATION", investigation });
    }
    if (dialogueChanged || learningChanged) {
        const nextDialogue = ensureDialogue(dialogue);
        nextDialogue.learning = learningChanged || learning ? learning ?? null : nextDialogue.learning ?? null;
        ops.push({ op: "SET_DIALOGUE", dialogue: nextDialogue });
    }
    if (caseOutcomeChanged) {
        ops.push({ op: "SET_CASE_OUTCOME", case_outcome: caseOutcome });
    }
    if (caseRecapChanged) {
        ops.push({ op: "SET_CASE_RECAP", case_recap: caseRecap });
    }

    return {
        schema_version: payload.schema_version,
        from_tick: payload.from_tick,
        to_tick: payload.to_tick,
        prev_step_hash: payload.prev_step_hash,
        step_hash: payload.step_hash,
        ops,
    };
}

type DiffOpFor<T extends DiffOp["op"]> = Extract<DiffOp, { op: T }>;

function normalizeWorldMeta(clock: Record<string, unknown> | null): WorldMeta | undefined {
    if (!clock) return undefined;
    return {
        world_output: asNumber(clock.world_output) ?? 0,
        day_index: asNumber(clock.day_index) ?? undefined,
        tick_in_day: asNumber(clock.tick_in_day) ?? undefined,
        time_of_day: asNumber(clock.time_of_day) ?? undefined,
        day_phase: asString(clock.day_phase) ?? undefined,
    };
}

function normalizeNpcSemanticSlice(rows: unknown[]): KvpNpcSemanticState[] {
    return rows.filter((row): row is KvpNpcSemanticState => Boolean(asRecord(row)));
}

function normalizeInvestigationSlice(
    value: Record<string, unknown> | null
): KvpInvestigationState | null {
    if (!value) return null;
    return {
        truth_epoch: asNumber(value.truth_epoch) ?? 1,
        objects: asArray(value.objects) as KvpInvestigationState["objects"],
        evidence: {
            discovered_ids: asStringArray(asRecord(value.evidence)?.discovered_ids),
            collected_ids: asStringArray(asRecord(value.evidence)?.collected_ids),
            observed_not_collected_ids: asStringArray(asRecord(value.evidence)?.observed_not_collected_ids),
        },
        facts: {
            known_fact_ids: asStringArray(asRecord(value.facts)?.known_fact_ids),
        },
        contradictions: {
            unlockable_edge_ids: asStringArray(asRecord(value.contradictions)?.unlockable_edge_ids),
            known_edge_ids: asStringArray(asRecord(value.contradictions)?.known_edge_ids),
            required_for_accusation: asBoolean(asRecord(value.contradictions)?.required_for_accusation) ?? false,
            requirement_satisfied: asBoolean(asRecord(value.contradictions)?.requirement_satisfied) ?? false,
        },
    };
}

function normalizeDialogueSlice(args: {
    dialogue: Record<string, unknown> | null;
    learning: Record<string, unknown> | null;
}): KvpDialogueState | null {
    const { dialogue, learning } = args;
    if (!dialogue && !learning) return null;

    const next: KvpDialogueState = {
        truth_epoch: asNumber(dialogue?.truth_epoch) ?? 1,
        active_scene_id: asNullableString(dialogue?.active_scene_id),
        scene_completion: asArray(dialogue?.scene_completion) as KvpDialogueState["scene_completion"],
        surfaced_scene_ids: asStringArray(dialogue?.surfaced_scene_ids),
        revealed_fact_ids: asStringArray(dialogue?.revealed_fact_ids),
        recent_turns: asArray(dialogue?.recent_turns) as KvpDialogueState["recent_turns"],
        summary_rules: {
            required_scene_ids: asStringArray(asRecord(dialogue?.summary_rules)?.required_scene_ids),
            current_scene_min_fact_count: asNullableNumber(asRecord(dialogue?.summary_rules)?.current_scene_min_fact_count),
        },
        contradiction_requirement_satisfied:
            asBoolean(dialogue?.contradiction_requirement_satisfied) ?? false,
        learning: normalizeLearningSlice(learning, asNullableString(dialogue?.active_scene_id)),
    };
    return next;
}

function normalizeLearningSlice(
    value: Record<string, unknown> | null,
    fallbackActiveSceneId: string | null
): KvpLearningState | null {
    if (!value) return null;
    return {
        difficulty_profile: asString(value.difficulty_profile) ?? "D0",
        active_scene_id: asNullableString(value.active_scene_id) ?? fallbackActiveSceneId,
        current_hint_level: asString(value.current_hint_level) ?? "soft_hint",
        summary_by_scene: asArray(value.summary_by_scene) as KvpLearningState["summary_by_scene"],
        minigames: asArray(value.minigames) as KvpLearningState["minigames"],
        scaffolding_policy: (
            asRecord(value.scaffolding_policy) ?? defaultScaffoldingPolicy()
        ) as KvpLearningState["scaffolding_policy"],
    };
}

function normalizeOutcomeSlice(
    value: Record<string, unknown> | null
): KvpCaseOutcomeState | null {
    if (!value) return null;
    return {
        truth_epoch: asNumber(value.truth_epoch) ?? 1,
        primary_outcome: asString(value.primary_outcome) ?? "in_progress",
        terminal: asBoolean(value.terminal) ?? false,
        recovery_success: asBoolean(value.recovery_success) ?? false,
        accusation_success: asBoolean(value.accusation_success) ?? false,
        soft_fail: asBoolean(value.soft_fail) ?? false,
        best_outcome: asBoolean(value.best_outcome) ?? false,
        contradiction_required_for_accusation:
            asBoolean(value.contradiction_required_for_accusation) ?? false,
        contradiction_requirement_satisfied:
            asBoolean(value.contradiction_requirement_satisfied) ?? false,
        quiet_recovery: asBoolean(value.quiet_recovery) ?? false,
        public_escalation: asBoolean(value.public_escalation) ?? false,
        soft_fail_latched: asBoolean(value.soft_fail_latched) ?? false,
        best_outcome_awarded: asBoolean(value.best_outcome_awarded) ?? false,
        soft_fail_reasons: asStringArray(value.soft_fail_reasons),
        continuity_flags: asStringArray(value.continuity_flags),
    };
}

function normalizeRecapSlice(
    value: Record<string, unknown> | null
): KvpCaseRecapState | null {
    if (!value) return null;
    return {
        truth_epoch: asNumber(value.truth_epoch) ?? 1,
        available: asBoolean(value.available) ?? false,
        final_outcome_type: asString(value.final_outcome_type) ?? "in_progress",
        resolution_path: asString(value.resolution_path) ?? "none",
        resolution_path_components: asStringArray(value.resolution_path_components),
        key_fact_ids: asStringArray(value.key_fact_ids),
        key_evidence_ids: asStringArray(value.key_evidence_ids),
        key_action_flags: asStringArray(value.key_action_flags),
        contradiction_used: asBoolean(value.contradiction_used) ?? false,
        contradiction_action_flags: asStringArray(value.contradiction_action_flags),
        contradiction_requirement_satisfied: asBoolean(value.contradiction_requirement_satisfied) ?? false,
        relationship_result_flags: asStringArray(value.relationship_result_flags),
        soft_fail: {
            triggered: asBoolean(asRecord(value.soft_fail)?.triggered) ?? false,
            latched: asBoolean(asRecord(value.soft_fail)?.latched) ?? false,
            trigger_conditions: asStringArray(asRecord(value.soft_fail)?.trigger_conditions),
            item_left_building: asBoolean(asRecord(value.soft_fail)?.item_left_building) ?? false,
        },
        best_outcome: {
            awarded: asBoolean(asRecord(value.best_outcome)?.awarded) ?? false,
            quiet_recovery: asBoolean(asRecord(value.best_outcome)?.quiet_recovery) ?? false,
            no_public_escalation: asBoolean(asRecord(value.best_outcome)?.no_public_escalation) ?? false,
            strong_key_trust: asBoolean(asRecord(value.best_outcome)?.strong_key_trust) ?? false,
        },
        continuity_flags: asStringArray(value.continuity_flags),
    };
}

function ensureInvestigation(
    value: KvpInvestigationState | null
): KvpInvestigationState {
    if (value) return value;
    return {
        truth_epoch: 1,
        objects: [],
        evidence: {
            discovered_ids: [],
            collected_ids: [],
            observed_not_collected_ids: [],
        },
        facts: {
            known_fact_ids: [],
        },
        contradictions: {
            unlockable_edge_ids: [],
            known_edge_ids: [],
            required_for_accusation: false,
            requirement_satisfied: false,
        },
    };
}

function ensureDialogue(value: KvpDialogueState | null): KvpDialogueState {
    if (value) return value;
    return {
        truth_epoch: 1,
        active_scene_id: null,
        scene_completion: [],
        surfaced_scene_ids: [],
        revealed_fact_ids: [],
        recent_turns: [],
        summary_rules: {
            required_scene_ids: [],
            current_scene_min_fact_count: null,
        },
        contradiction_requirement_satisfied: false,
        learning: null,
    };
}

function ensureLearning(
    value: KvpLearningState | null,
    activeSceneId: string | null
): KvpLearningState {
    if (value) return value;
    return {
        difficulty_profile: "D0",
        active_scene_id: activeSceneId,
        current_hint_level: "soft_hint",
        summary_by_scene: [],
        minigames: [],
        scaffolding_policy: defaultScaffoldingPolicy(),
    };
}

function defaultScaffoldingPolicy(): KvpLearningScaffoldingPolicy {
    return {
        scene_id: null,
        current_hint_level: "soft_hint",
        current_hint_rank: 0,
        allowed_hint_levels: ["soft_hint"],
        recommended_mode: "hint",
        english_meta_allowed: false,
        french_action_required: true,
        reason_code: "default",
        soft_hint_key: null,
        sentence_stem_key: null,
        rephrase_set_id: null,
        english_meta_key: null,
        prompt_generosity: "default",
        confirmation_strength: "default",
        summary_strictness: "default",
        language_support_level: "default",
        target_minigame_id: null,
    };
}

function ensureCaseOutcome(value: KvpCaseOutcomeState | null): KvpCaseOutcomeState {
    if (value) return value;
    return {
        truth_epoch: 1,
        primary_outcome: "in_progress",
        terminal: false,
        recovery_success: false,
        accusation_success: false,
        soft_fail: false,
        best_outcome: false,
        contradiction_required_for_accusation: false,
        contradiction_requirement_satisfied: false,
        quiet_recovery: false,
        public_escalation: false,
        soft_fail_latched: false,
        best_outcome_awarded: false,
        soft_fail_reasons: [],
        continuity_flags: [],
    };
}

function toWorldEvent(value: Record<string, unknown>, tick: number): KvpEvent | null {
    const eventId = stablePositiveInt(JSON.stringify(value)) ?? 0;
    return {
        tick,
        event_id: eventId,
        origin: "live_event",
        payload: deepClone(value),
    };
}

function upsertByStringId<
    TRow extends Record<string, unknown>,
    TKey extends keyof TRow & string,
>(
    rows: TRow[],
    next: TRow,
    keyField: TKey
): TRow[] {
    const key = asString(next[keyField]);
    if (!key) return rows;
    const filtered = rows.filter((row) => asString(row[keyField]) !== key);
    return [...filtered, next];
}

function appendUniqueSorted(values: string[], value: string): string[] {
    const out = new Set(values);
    out.add(value);
    return Array.from(out).sort((a, b) => a.localeCompare(b));
}

function stablePositiveInt(value: string): number | null {
    let hash = 0;
    for (let idx = 0; idx < value.length; idx += 1) {
        hash = ((hash << 5) - hash + value.charCodeAt(idx)) | 0;
    }
    return Math.abs(hash);
}

function deepClone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
}

function asRecord(value: unknown): Record<string, unknown> | null {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    return value as Record<string, unknown>;
}

function asArray(value: unknown): unknown[] {
    if (!Array.isArray(value)) return [];
    return value.map((row) => deepClone(row));
}

function asString(value: unknown): string | null {
    return typeof value === "string" && value.length > 0 ? value : null;
}

function asNullableString(value: unknown): string | null {
    if (value === null) return null;
    return asString(value);
}

function asNumber(value: unknown): number | null {
    if (typeof value === "number" && Number.isFinite(value)) return value;
    return null;
}

function asNullableNumber(value: unknown): number | null {
    if (value === null) return null;
    return asNumber(value);
}

function asBoolean(value: unknown): boolean | null {
    if (typeof value === "boolean") return value;
    return null;
}

function asStringArray(value: unknown): string[] {
    if (!Array.isArray(value)) return [];
    return value
        .map((row) => asString(row))
        .filter((row): row is string => row !== null);
}
