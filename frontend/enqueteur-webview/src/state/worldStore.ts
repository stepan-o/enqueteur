// src/state/worldStore.ts

export type KvpRoom = {
    room_id: number;
    label: string;
    kind_code: number;
    occupants: number[];
    items: number[];
    neighbors: number[];
    tension_tier: string | null;
    highlight: boolean | null;
    height?: number | null;
    bounds?: { min_x: number; min_y: number; max_x: number; max_y: number } | null;
    zone?: string | null;
    level?: number | null;
};

export type KvpTransform = {
    room_id: number;
    x: number;
    y: number;
};

export type KvpAgent = {
    agent_id: number;
    room_id: number;
    role_code: number;
    generation: number;
    profile_traits: Record<string, unknown>;
    identity_vector: unknown[];
    persona_style_vector: unknown[] | null;
    drives: Record<string, unknown>;
    emotions: Record<string, unknown>;
    key_relationships: unknown[];
    active_motives: unknown[];
    plan: unknown | null;
    transform: KvpTransform;
    action_state_code: number;
    durability: number;
    energy: number;
    money: number;
    smartness: number;
    toughness: number;
    obedience: number;
    mission_alignment: number;
    narrative_state_ref: string | null;
    cached_summary_ref: string | null;
};

export type KvpItem = {
    item_id: number;
    room_id: number;
    owner_agent_id: number | null;
    status_code: number;
    label: string;
};

export type KvpObject = {
    object_id: number;
    class_code: string;
    room_id: number;
    tile_x: number;
    tile_y: number;
    size_w: number;
    size_h: number;
    orientation: number;
    scale: number;
    height: number | null;
    durability: number;
    efficiency: number;
    status_code: number;
    occupant_agent_id: number | null;
    ticks_in_state: number;
};

export type WorldMeta = {
    world_output: number;
    day_index?: number;
    ticks_per_day?: number;
    tick_in_day?: number;
    time_of_day?: number;
    day_phase?: string;
    phase_progress?: number;
};

export type KvpEvent = {
    tick: number;
    event_id: number;
    origin: string;
    payload: Record<string, unknown>;
};

export type KvpCaseVisibleSlice = {
    public_room_ids: string[];
    public_object_ids: string[];
    starting_scene_id: string;
    starting_known_fact_ids: string[];
};

export type KvpCaseStateSlice = {
    case_id: string;
    seed: string;
    truth_epoch: number;
    visible_case_slice: KvpCaseVisibleSlice;
};

export type KvpNpcSemanticCardState = {
    portrait_variant: string;
    tell_cue: string | null;
    suggested_interaction_mode: string;
    trust_trend: string;
};

export type KvpNpcSemanticState = {
    npc_id: string;
    current_room_id: string;
    availability: string;
    trust: number;
    stress: number;
    stance: string;
    emotion: string;
    soft_alignment_hint: string;
    visible_behavior_flags: string[];
    current_scene_id: string | null;
    card_state: KvpNpcSemanticCardState;
};

export type KvpInvestigationObjectState = {
    object_id: string;
    affordances: string[];
    observed_affordances: string[];
    known_state: Record<string, unknown>;
};

export type KvpInvestigationEvidenceState = {
    discovered_ids: string[];
    collected_ids: string[];
    observed_not_collected_ids: string[];
};

export type KvpInvestigationFactState = {
    known_fact_ids: string[];
};

export type KvpContradictionAvailabilityState = {
    unlockable_edge_ids: string[];
    known_edge_ids: string[];
    required_for_accusation: boolean;
    requirement_satisfied: boolean;
};

export type KvpInvestigationState = {
    truth_epoch: number;
    objects: KvpInvestigationObjectState[];
    evidence: KvpInvestigationEvidenceState;
    facts: KvpInvestigationFactState;
    contradictions: KvpContradictionAvailabilityState;
};

export type KvpDialogueSceneCompletion = {
    scene_id: string;
    completion_state: string;
};

export type KvpDialogueSummaryRules = {
    required_scene_ids: string[];
    current_scene_min_fact_count: number | null;
};

export type KvpLearningSceneSummaryState = {
    scene_id: string;
    required: boolean;
    min_fact_count: number;
    effective_min_fact_count: number;
    required_key_fact_ids: string[];
    required_key_fact_count: number;
    attempt_count: number;
    completed: boolean;
    summary_passed: boolean | null;
    last_summary_code: string | null;
    status: string;
    strictness_mode: string;
};

export type KvpLearningMinigameState = {
    minigame_id: string;
    attempt_count: number;
    completed: boolean;
    score: number;
    max_score: number;
    pass_score_required: number;
    gate_open: boolean;
    gate_code: string;
    retry_recommended: boolean;
    status: string;
};

export type KvpLearningScaffoldingPolicy = {
    scene_id: string | null;
    current_hint_level: string;
    current_hint_rank: number;
    allowed_hint_levels: string[];
    recommended_mode: string;
    english_meta_allowed: boolean;
    french_action_required: boolean;
    reason_code: string;
    soft_hint_key: string | null;
    sentence_stem_key: string | null;
    rephrase_set_id: string | null;
    english_meta_key: string | null;
    prompt_generosity: string;
    confirmation_strength: string;
    summary_strictness: string;
    language_support_level: string;
    target_minigame_id: string | null;
};

export type KvpLearningState = {
    difficulty_profile: string;
    active_scene_id: string | null;
    current_hint_level: string;
    summary_by_scene: KvpLearningSceneSummaryState[];
    minigames: KvpLearningMinigameState[];
    scaffolding_policy: KvpLearningScaffoldingPolicy;
};

export type KvpDialogueTurnLog = {
    turn_index: number;
    scene_id: string;
    npc_id: string;
    intent_id: string;
    status: string;
    code: string;
    outcome: string;
    response_mode: string;
    revealed_fact_ids: string[];
    trust_delta: number;
    stress_delta: number;
    repair_response_mode: string | null;
    summary_check_code: string | null;
    presentation_source?: string | null;
    presentation_reason_code?: string | null;
    presentation_metadata?: string[];
    npc_utterance_text?: string | null;
    short_rephrase_line?: string | null;
    hint_line?: string | null;
    summary_prompt_line?: string | null;
};

export type KvpDialogueState = {
    truth_epoch: number;
    active_scene_id: string | null;
    scene_completion: KvpDialogueSceneCompletion[];
    surfaced_scene_ids: string[];
    revealed_fact_ids: string[];
    recent_turns: KvpDialogueTurnLog[];
    summary_rules: KvpDialogueSummaryRules;
    contradiction_requirement_satisfied: boolean;
    learning?: KvpLearningState | null;
};

export type KvpCaseOutcomeState = {
    truth_epoch: number;
    primary_outcome: string;
    terminal: boolean;
    recovery_success: boolean;
    accusation_success: boolean;
    soft_fail: boolean;
    best_outcome: boolean;
    contradiction_required_for_accusation: boolean;
    contradiction_requirement_satisfied: boolean;
    quiet_recovery: boolean;
    public_escalation: boolean;
    soft_fail_latched?: boolean;
    best_outcome_awarded?: boolean;
    soft_fail_reasons?: string[];
    continuity_flags?: string[];
};

export type KvpCaseRecapState = {
    truth_epoch: number;
    available: boolean;
    final_outcome_type: string;
    resolution_path: string;
    resolution_path_components: string[];
    key_fact_ids: string[];
    key_evidence_ids: string[];
    key_action_flags: string[];
    contradiction_used: boolean;
    contradiction_action_flags: string[];
    contradiction_requirement_satisfied: boolean;
    relationship_result_flags: string[];
    soft_fail: {
        triggered: boolean;
        latched: boolean;
        trigger_conditions: string[];
        item_left_building: boolean;
    };
    best_outcome: {
        awarded: boolean;
        quiet_recovery: boolean;
        no_public_escalation: boolean;
        strong_key_trust: boolean;
    };
    continuity_flags: string[];
};

export type KvpState = {
    rooms: KvpRoom[];
    agents: KvpAgent[];
    items: KvpItem[];
    objects?: KvpObject[];
    world?: WorldMeta;
    events: KvpEvent[];
    case?: KvpCaseStateSlice;
    npc_semantic?: KvpNpcSemanticState[];
    investigation?: KvpInvestigationState;
    dialogue?: KvpDialogueState;
    case_outcome?: KvpCaseOutcomeState;
    case_recap?: KvpCaseRecapState;
    debug?: unknown;
};

export type FullSnapshotPayload = {
    schema_version: string;
    tick: number;
    state: KvpState;
    step_hash: string;
};

export type DiffOp =
    | { op: "SET_WORLD"; world: WorldMeta }
    | { op: "CLEAR_WORLD" }
    | { op: "UPSERT_ROOM"; room: KvpRoom }
    | { op: "REMOVE_ROOM"; room_id: number }
    | { op: "UPSERT_AGENT"; agent: KvpAgent }
    | { op: "REMOVE_AGENT"; agent_id: number }
    | { op: "UPSERT_ITEM"; item: KvpItem }
    | { op: "REMOVE_ITEM"; item_id: number }
    | { op: "UPSERT_OBJECT"; object: KvpObject }
    | { op: "REMOVE_OBJECT"; object_id: number }
    | { op: "UPSERT_EVENT"; event: KvpEvent }
    | { op: "REMOVE_EVENT"; event_key: { tick: number; event_id: number } }
    | { op: "SET_CASE"; case: KvpCaseStateSlice | null }
    | { op: "SET_NPC_SEMANTIC"; npc_semantic: KvpNpcSemanticState[] }
    | { op: "SET_INVESTIGATION"; investigation: KvpInvestigationState | null }
    | { op: "SET_DIALOGUE"; dialogue: KvpDialogueState | null }
    | { op: "SET_CASE_OUTCOME"; case_outcome: KvpCaseOutcomeState | null }
    | { op: "SET_CASE_RECAP"; case_recap: KvpCaseRecapState | null };

export type FrameDiffPayload = {
    schema_version: string;
    from_tick: number;
    to_tick: number;
    prev_step_hash?: string | null;
    ops: DiffOp[];
    step_hash: string;
};

export type KernelHello = {
    engine_name: string;
    engine_version: string;
    schema_version: string;
    world_id: string;
    run_id: string;
    seed: string | number;
    tick_rate_hz: number;
    time_origin_ms?: number;
};

export type RunAnchors = {
    engine_name: string;
    engine_version: string;
    schema_version: string;
    world_id: string;
    run_id: string;
    seed: string | number;
    tick_rate_hz: number;
    time_origin_ms: number;
};

export type RenderSpec = {
    coord_system?: {
        axis?: { x_positive: string; y_positive: string };
        bounds?: { min_x: number; min_y: number; max_x: number; max_y: number };
        origin?: { x: number; y: number };
        units?: string;
        units_per_tile?: number;
    };
    projection?: { kind: string; recommended_iso_tile_w?: number; recommended_iso_tile_h?: number };
    draw_order?: Record<string, unknown>;
    local_sort_key?: Record<string, unknown>;
    z_layer?: Record<string, unknown>;
    asset_resolution?: Record<string, unknown>;
};

export type WorldState = {
    mode: "live" | "offline";
    tick: number;
    stepHash?: string;
    connected: boolean;
    desynced: boolean;
    desyncReason?: string;
    kernelHello?: KernelHello;
    runAnchors?: RunAnchors;
    renderSpec?: RenderSpec;
    world: WorldMeta | null;
    rooms: Map<number, KvpRoom>;
    agents: Map<number, KvpAgent>;
    items: Map<number, KvpItem>;
    objects: Map<number, KvpObject>;
    events: Map<string, KvpEvent>;
    caseState: KvpCaseStateSlice | null;
    npcSemantic: KvpNpcSemanticState[];
    investigation: KvpInvestigationState | null;
    dialogue: KvpDialogueState | null;
    caseOutcome: KvpCaseOutcomeState | null;
    caseRecap: KvpCaseRecapState | null;
    debug?: unknown;
};

export type WorldStoreSubscriber = (s: WorldState) => void;

export class WorldStore {
    private state: WorldState;
    private readonly subs = new Set<WorldStoreSubscriber>();

    constructor() {
        this.state = {
            mode: "live",
            tick: 0,
            stepHash: undefined,
            connected: false,
            desynced: false,
            desyncReason: undefined,
            kernelHello: undefined,
            runAnchors: undefined,
            renderSpec: undefined,
            world: null,
            rooms: new Map(),
            agents: new Map(),
            items: new Map(),
            objects: new Map(),
            events: new Map(),
            caseState: null,
            npcSemantic: [],
            investigation: null,
            dialogue: null,
            caseOutcome: null,
            caseRecap: null,
            debug: undefined,
        };
    }

    subscribe(cb: WorldStoreSubscriber): () => void {
        this.subs.add(cb);
        cb(this.state);
        return () => this.subs.delete(cb);
    }

    getState(): WorldState {
        return this.state;
    }

    setMode(mode: WorldState["mode"]): void {
        this.state = { ...this.state, mode };
        this.emit();
    }

    setConnected(connected: boolean): void {
        this.state = { ...this.state, connected };
        this.emit();
    }

    setKernelHello(hello: KernelHello): void {
        this.state = { ...this.state, kernelHello: hello };
        this.emit();
    }

    setRunAnchors(anchors: RunAnchors): void {
        this.state = { ...this.state, runAnchors: anchors };
        this.emit();
    }

    setRenderSpec(spec: RenderSpec): void {
        this.state = { ...this.state, renderSpec: spec };
        this.emit();
    }

    markDesync(reason: string): void {
        this.state = { ...this.state, desynced: true, desyncReason: reason };
        this.emit();
    }

    clearDesync(): void {
        if (!this.state.desynced) return;
        this.state = { ...this.state, desynced: false, desyncReason: undefined };
        this.emit();
    }

    applySnapshot(payload: FullSnapshotPayload): void {
        if (!payload || !payload.state) {
            this.markDesync("Invalid snapshot payload");
            return;
        }

        const rooms = new Map<number, KvpRoom>();
        for (const r of payload.state.rooms ?? []) rooms.set(r.room_id, r);

        const agents = new Map<number, KvpAgent>();
        for (const a of payload.state.agents ?? []) agents.set(a.agent_id, a);

        const items = new Map<number, KvpItem>();
        for (const i of payload.state.items ?? []) items.set(i.item_id, i);

        const objects = new Map<number, KvpObject>();
        for (const o of payload.state.objects ?? []) objects.set(o.object_id, o);

        const events = new Map<string, KvpEvent>();
        for (const e of payload.state.events ?? []) events.set(eventKey(e), e);

        this.state = {
            ...this.state,
            tick: payload.tick,
            stepHash: payload.step_hash,
            desynced: false,
            desyncReason: undefined,
            world: payload.state.world ?? null,
            rooms,
            agents,
            items,
            objects,
            events,
            caseState: cloneCaseState(payload.state.case),
            npcSemantic: cloneNpcSemantic(payload.state.npc_semantic),
            investigation: cloneInvestigationState(payload.state.investigation),
            dialogue: cloneDialogueState(payload.state.dialogue),
            caseOutcome: cloneCaseOutcomeState(payload.state.case_outcome),
            caseRecap: cloneCaseRecapState(payload.state.case_recap),
            debug: payload.state.debug,
        };

        this.emit();
    }

    applyDiff(payload: FrameDiffPayload): void {
        if (this.state.desynced) return;
        if (!payload || !Array.isArray(payload.ops)) {
            this.markDesync("Invalid diff payload");
            return;
        }

        if (typeof payload.prev_step_hash === "string" && this.state.stepHash && payload.prev_step_hash !== this.state.stepHash) {
            this.markDesync("Step hash mismatch (diff chain broken)");
            return;
        }

        if (this.state.tick && payload.from_tick !== this.state.tick) {
            this.markDesync(`Tick mismatch (expected ${this.state.tick}, got ${payload.from_tick})`);
            return;
        }

        const rooms = new Map(this.state.rooms);
        const agents = new Map(this.state.agents);
        const items = new Map(this.state.items);
        const objects = new Map(this.state.objects);
        const events = new Map(this.state.events);
        let world = this.state.world;
        let caseState = this.state.caseState;
        let npcSemantic = this.state.npcSemantic;
        let investigation = this.state.investigation;
        let dialogue = this.state.dialogue;
        let caseOutcome = this.state.caseOutcome;
        let caseRecap = this.state.caseRecap;

        for (const op of payload.ops) {
            switch (op.op) {
                case "SET_WORLD":
                    world = op.world;
                    break;
                case "CLEAR_WORLD":
                    world = null;
                    break;
                case "UPSERT_ROOM":
                    rooms.set(op.room.room_id, op.room);
                    break;
                case "REMOVE_ROOM":
                    rooms.delete(op.room_id);
                    break;
                case "UPSERT_AGENT":
                    agents.set(op.agent.agent_id, op.agent);
                    break;
                case "REMOVE_AGENT":
                    agents.delete(op.agent_id);
                    break;
                case "UPSERT_ITEM":
                    items.set(op.item.item_id, op.item);
                    break;
                case "REMOVE_ITEM":
                    items.delete(op.item_id);
                    break;
                case "UPSERT_OBJECT":
                    objects.set(op.object.object_id, op.object);
                    break;
                case "REMOVE_OBJECT":
                    objects.delete(op.object_id);
                    break;
                case "UPSERT_EVENT":
                    events.set(eventKey(op.event), op.event);
                    break;
                case "REMOVE_EVENT":
                    events.delete(eventKeyFromKey(op.event_key));
                    break;
                case "SET_CASE":
                    caseState = cloneCaseState(op.case ?? undefined);
                    break;
                case "SET_NPC_SEMANTIC":
                    npcSemantic = cloneNpcSemantic(op.npc_semantic);
                    break;
                case "SET_INVESTIGATION":
                    investigation = cloneInvestigationState(op.investigation ?? undefined);
                    break;
                case "SET_DIALOGUE":
                    dialogue = cloneDialogueState(op.dialogue ?? undefined);
                    break;
                case "SET_CASE_OUTCOME":
                    caseOutcome = cloneCaseOutcomeState(op.case_outcome ?? undefined);
                    break;
                case "SET_CASE_RECAP":
                    caseRecap = cloneCaseRecapState(op.case_recap ?? undefined);
                    break;
                default:
                    this.markDesync(`Unknown diff op: ${(op as { op: string }).op}`);
                    return;
            }
        }

        this.state = {
            ...this.state,
            tick: payload.to_tick,
            stepHash: payload.step_hash,
            world,
            rooms,
            agents,
            items,
            objects,
            events,
            caseState,
            npcSemantic,
            investigation,
            dialogue,
            caseOutcome,
            caseRecap,
        };

        this.emit();
    }

    private emit(): void {
        for (const cb of this.subs) cb(this.state);
    }
}

export function eventKey(ev: KvpEvent): string {
    return `${ev.tick}:${ev.event_id}`;
}

export function eventKeyFromKey(key: { tick: number; event_id: number }): string {
    return `${key.tick}:${key.event_id}`;
}

function cloneCaseState(value: KvpCaseStateSlice | undefined): KvpCaseStateSlice | null {
    if (!value) return null;
    return {
        ...value,
        visible_case_slice: {
            ...value.visible_case_slice,
            public_room_ids: [...value.visible_case_slice.public_room_ids],
            public_object_ids: [...value.visible_case_slice.public_object_ids],
            starting_known_fact_ids: [...value.visible_case_slice.starting_known_fact_ids],
        },
    };
}

function cloneNpcSemantic(value: KvpNpcSemanticState[] | undefined): KvpNpcSemanticState[] {
    if (!value) return [];
    return value.map((row) => ({
        ...row,
        visible_behavior_flags: [...row.visible_behavior_flags],
        card_state: { ...row.card_state },
    }));
}

function cloneInvestigationState(value: KvpInvestigationState | undefined): KvpInvestigationState | null {
    if (!value) return null;
    return {
        ...value,
        objects: value.objects.map((obj) => ({
            ...obj,
            affordances: [...obj.affordances],
            observed_affordances: [...obj.observed_affordances],
            known_state: { ...obj.known_state },
        })),
        evidence: {
            ...value.evidence,
            discovered_ids: [...value.evidence.discovered_ids],
            collected_ids: [...value.evidence.collected_ids],
            observed_not_collected_ids: [...value.evidence.observed_not_collected_ids],
        },
        facts: {
            ...value.facts,
            known_fact_ids: [...value.facts.known_fact_ids],
        },
        contradictions: {
            ...value.contradictions,
            unlockable_edge_ids: [...value.contradictions.unlockable_edge_ids],
            known_edge_ids: [...value.contradictions.known_edge_ids],
        },
    };
}

function cloneDialogueState(value: KvpDialogueState | undefined): KvpDialogueState | null {
    if (!value) return null;
    return {
        ...value,
        scene_completion: value.scene_completion.map((row) => ({ ...row })),
        surfaced_scene_ids: [...value.surfaced_scene_ids],
        revealed_fact_ids: [...value.revealed_fact_ids],
        recent_turns: value.recent_turns.map((turn) => ({
            ...turn,
            revealed_fact_ids: [...turn.revealed_fact_ids],
            presentation_metadata: [...(turn.presentation_metadata ?? [])],
        })),
        summary_rules: {
            ...value.summary_rules,
            required_scene_ids: [...value.summary_rules.required_scene_ids],
        },
        learning: value.learning
                ? {
                  ...value.learning,
                  summary_by_scene: value.learning.summary_by_scene.map((row) => ({
                      ...row,
                      required_key_fact_ids: [...row.required_key_fact_ids],
                      required_key_fact_count:
                          typeof row.required_key_fact_count === "number"
                              ? row.required_key_fact_count
                              : row.required_key_fact_ids.length,
                  })),
                  minigames: value.learning.minigames.map((row) => ({ ...row })),
                  scaffolding_policy: {
                      ...value.learning.scaffolding_policy,
                      allowed_hint_levels: [...value.learning.scaffolding_policy.allowed_hint_levels],
                  },
              }
            : null,
    };
}

function cloneCaseOutcomeState(value: KvpCaseOutcomeState | undefined): KvpCaseOutcomeState | null {
    if (!value) return null;
    return {
        ...value,
        soft_fail_reasons: [...(value.soft_fail_reasons ?? [])],
        continuity_flags: [...(value.continuity_flags ?? [])],
    };
}

function cloneCaseRecapState(value: KvpCaseRecapState | undefined): KvpCaseRecapState | null {
    if (!value) return null;
    return {
        ...value,
        resolution_path_components: [...value.resolution_path_components],
        key_fact_ids: [...value.key_fact_ids],
        key_evidence_ids: [...value.key_evidence_ids],
        key_action_flags: [...value.key_action_flags],
        contradiction_action_flags: [...value.contradiction_action_flags],
        relationship_result_flags: [...value.relationship_result_flags],
        soft_fail: {
            ...value.soft_fail,
            trigger_conditions: [...value.soft_fail.trigger_conditions],
        },
        best_outcome: { ...value.best_outcome },
        continuity_flags: [...value.continuity_flags],
    };
}
