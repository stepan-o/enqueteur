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
};

export type KvpEvent = {
    tick: number;
    event_id: number;
    origin: string;
    payload: Record<string, unknown>;
};

export type KvpState = {
    rooms: KvpRoom[];
    agents: KvpAgent[];
    items: KvpItem[];
    objects?: KvpObject[];
    events: KvpEvent[];
    debug?: unknown;
};

export type FullSnapshotPayload = {
    schema_version: string;
    tick: number;
    state: KvpState;
    step_hash: string;
};

export type DiffOp =
    | { op: "UPSERT_ROOM"; room: KvpRoom }
    | { op: "REMOVE_ROOM"; room_id: number }
    | { op: "UPSERT_AGENT"; agent: KvpAgent }
    | { op: "REMOVE_AGENT"; agent_id: number }
    | { op: "UPSERT_ITEM"; item: KvpItem }
    | { op: "REMOVE_ITEM"; item_id: number }
    | { op: "UPSERT_OBJECT"; object: KvpObject }
    | { op: "REMOVE_OBJECT"; object_id: number }
    | { op: "UPSERT_EVENT"; event: KvpEvent }
    | { op: "REMOVE_EVENT"; event_key: { tick: number; event_id: number } };

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
    seed: number;
    tick_rate_hz: number;
    time_origin_ms?: number;
};

export type RunAnchors = {
    engine_name: string;
    engine_version: string;
    schema_version: string;
    world_id: string;
    run_id: string;
    seed: number;
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
    rooms: Map<number, KvpRoom>;
    agents: Map<number, KvpAgent>;
    items: Map<number, KvpItem>;
    objects: Map<number, KvpObject>;
    events: Map<string, KvpEvent>;
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
            rooms: new Map(),
            agents: new Map(),
            items: new Map(),
            objects: new Map(),
            events: new Map(),
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
            rooms,
            agents,
            items,
            objects,
            events,
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

        for (const op of payload.ops) {
            switch (op.op) {
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
                default:
                    this.markDesync(`Unknown diff op: ${(op as { op: string }).op}`);
                    return;
            }
        }

        this.state = {
            ...this.state,
            tick: payload.to_tick,
            stepHash: payload.step_hash,
            rooms,
            agents,
            items,
            objects,
            events,
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
