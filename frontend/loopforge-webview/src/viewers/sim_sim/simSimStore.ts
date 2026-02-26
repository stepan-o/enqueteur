import type { KernelHello } from "../../state/worldStore";

export const SIM_SIM_SCHEMA_VERSION = "sim_sim_1";

export type SimSimWorldMeta = {
    day: number;
    tick: number;
    phase: string;
    time: string;
    tick_hz: number;
    seed: number;
    run_id: string;
    world_id: string;
    security_lead?: string;
    config_hash?: string;
    config_id?: string;
};

export type SimSimWorkers = {
    dumb: number | null;
    smart: number | null;
};

export type SimSimOutputToday = {
    raw_brains_dumb: number;
    raw_brains_smart: number;
    washed_dumb: number;
    washed_smart: number;
    substrate_gallons: number;
    ribbon_yards: number;
};

export type SimSimAccidents = {
    count: number;
    casualties: number;
};

export type SimSimRoom = {
    room_id: number;
    name: string;
    unlocked_day: number;
    locked: boolean;
    supervisor: string | null;
    workers_assigned: SimSimWorkers;
    workers_present: SimSimWorkers;
    equipment_condition: number | null;
    stress: number | null;
    discipline: number | null;
    alignment: number | null;
    output_today: SimSimOutputToday;
    accidents_today: SimSimAccidents;
    bounds?: { min_x: number; min_y: number; max_x: number; max_y: number } | null;
    neighbors?: number[];
};

export type SimSimSupervisor = {
    code: string;
    name: string;
    unlocked_day: number;
    native_room: number;
    assigned_room: number | null;
    loyalty: number;
    confidence: number;
    influence: number;
    cooldown_days: number;
};

export type SimSimEvent = {
    tick: number;
    event_id: number;
    kind: string;
    room_id?: number;
    supervisor?: string;
    details?: Record<string, unknown>;
};

export type SimSimInventory = {
    cash: number;
    inventories: {
        raw_brains_dumb: number;
        raw_brains_smart: number;
        washed_dumb: number;
        washed_smart: number;
        substrate_gallons: number;
        ribbon_yards: number;
    };
    worker_pools?: {
        dumb_total: number;
        smart_total: number;
    };
};

export type SimSimRegime = {
    refactor_days: number;
    inversion_days: number;
    shutdown_except_brewery_today: boolean;
    weaving_boost_next_day: boolean;
    weaving_boost_multiplier_today?: number;
    global_accident_bonus: number;
    global_non_weaving_output_multiplier_today?: number;
    lockdown_today?: boolean;
};

export type SimSimPrompt = {
    prompt_id: string;
    kind: string;
    tick: number;
    choices: string[];
    status: string;
    selected_choice?: string | null;
    payload?: Record<string, unknown>;
};

export type SimSimSnapshotPayload = {
    schema_version: string;
    tick: number;
    state: {
        world_meta?: SimSimWorldMeta;
        rooms?: SimSimRoom[];
        supervisors?: SimSimSupervisor[];
        inventory?: SimSimInventory;
        regime?: SimSimRegime;
        events?: SimSimEvent[];
        prompts?: SimSimPrompt[];
    };
    step_hash: string;
};

export type SimSimFrameDiffPayload = {
    schema_version: string;
    from_tick: number;
    to_tick: number;
    prev_step_hash?: string | null;
    world_meta_update?: SimSimWorldMeta;
    room_updates?: SimSimRoom[];
    supervisor_updates?: SimSimSupervisor[];
    inventory_update?: SimSimInventory;
    regime_update?: SimSimRegime;
    events_append?: SimSimEvent[];
    prompts_update?: SimSimPrompt[];
    step_hash: string;
};

export type SimSimViewerState = {
    tick: number;
    stepHash?: string;
    schemaVersion?: string;
    lastMsgType?: string;
    lastAppliedDiffCount: number;
    diffsAppliedTotal: number;
    kernelHello?: KernelHello;
    worldMeta: SimSimWorldMeta | null;
    inventory: SimSimInventory | null;
    regime: SimSimRegime | null;
    rooms: Map<number, SimSimRoom>;
    supervisors: Map<string, SimSimSupervisor>;
    events: Map<string, SimSimEvent>;
    prompts: Map<string, SimSimPrompt>;
    desynced: boolean;
    desyncReason?: string;
};

export type SimSimStoreSubscriber = (s: SimSimViewerState) => void;

export class SimSimStore {
    private state: SimSimViewerState;
    private readonly subs = new Set<SimSimStoreSubscriber>();

    constructor() {
        this.state = {
            tick: 0,
            stepHash: undefined,
            schemaVersion: undefined,
            lastMsgType: undefined,
            lastAppliedDiffCount: 0,
            diffsAppliedTotal: 0,
            kernelHello: undefined,
            worldMeta: null,
            inventory: null,
            regime: null,
            rooms: new Map(),
            supervisors: new Map(),
            events: new Map(),
            prompts: new Map(),
            desynced: false,
            desyncReason: undefined,
        };
    }

    subscribe(cb: SimSimStoreSubscriber): () => void {
        this.subs.add(cb);
        cb(this.state);
        return () => this.subs.delete(cb);
    }

    setKernelHello(hello: KernelHello): void {
        this.state = {
            ...this.state,
            kernelHello: hello,
            schemaVersion: hello.schema_version,
            lastMsgType: "KERNEL_HELLO",
        };
        this.emit();
    }

    clearDesync(): void {
        if (!this.state.desynced) return;
        this.state = { ...this.state, desynced: false, desyncReason: undefined };
        this.emit();
    }

    markDesync(reason: string): void {
        this.state = { ...this.state, desynced: true, desyncReason: reason };
        this.emit();
    }

    applySnapshot(payload: SimSimSnapshotPayload): void {
        if (!payload || !payload.state) {
            this.markDesync("Invalid sim_sim snapshot payload");
            return;
        }
        if (payload.schema_version !== SIM_SIM_SCHEMA_VERSION) {
            this.markDesync(`sim_sim snapshot schema mismatch (${payload.schema_version})`);
            return;
        }

        const rooms = new Map<number, SimSimRoom>();
        for (const room of payload.state.rooms ?? []) rooms.set(room.room_id, room);

        const supervisors = new Map<string, SimSimSupervisor>();
        for (const supervisor of payload.state.supervisors ?? []) supervisors.set(supervisor.code, supervisor);

        const events = new Map<string, SimSimEvent>();
        for (const ev of payload.state.events ?? []) events.set(eventKey(ev), ev);
        const prompts = new Map<string, SimSimPrompt>();
        for (const prompt of payload.state.prompts ?? []) prompts.set(prompt.prompt_id, prompt);

        this.state = {
            ...this.state,
            tick: payload.tick,
            stepHash: payload.step_hash,
            schemaVersion: payload.schema_version,
            lastMsgType: "FULL_SNAPSHOT",
            lastAppliedDiffCount: 0,
            worldMeta: payload.state.world_meta ?? null,
            inventory: payload.state.inventory ?? null,
            regime: payload.state.regime ?? null,
            rooms,
            supervisors,
            events,
            prompts,
            desynced: false,
            desyncReason: undefined,
        };
        this.emit();
    }

    applyDiff(payload: SimSimFrameDiffPayload): void {
        if (this.state.desynced) return;
        if (!payload) {
            this.markDesync("Invalid sim_sim diff payload");
            return;
        }
        if (payload.schema_version !== SIM_SIM_SCHEMA_VERSION) {
            this.markDesync(`sim_sim diff schema mismatch (${payload.schema_version})`);
            return;
        }
        if (typeof payload.prev_step_hash === "string" && this.state.stepHash && payload.prev_step_hash !== this.state.stepHash) {
            this.markDesync("sim_sim step hash mismatch");
            return;
        }
        if (payload.from_tick !== this.state.tick) {
            this.markDesync(`sim_sim tick mismatch (expected ${this.state.tick}, got ${payload.from_tick})`);
            return;
        }

        const rooms = new Map(this.state.rooms);
        const supervisors = new Map(this.state.supervisors);
        const events = new Map(this.state.events);
        const prompts = new Map(this.state.prompts);
        let worldMeta = this.state.worldMeta;
        let inventory = this.state.inventory;
        let regime = this.state.regime;
        let appliedCount = 0;

        if (payload.world_meta_update) {
            worldMeta = payload.world_meta_update;
            appliedCount += 1;
        }
        for (const room of payload.room_updates ?? []) {
            rooms.set(room.room_id, room);
            appliedCount += 1;
        }
        for (const supervisor of payload.supervisor_updates ?? []) {
            supervisors.set(supervisor.code, supervisor);
            appliedCount += 1;
        }
        if (payload.inventory_update) {
            inventory = payload.inventory_update;
            appliedCount += 1;
        }
        if (payload.regime_update) {
            regime = payload.regime_update;
            appliedCount += 1;
        }
        for (const event of payload.events_append ?? []) {
            events.set(eventKey(event), event);
            appliedCount += 1;
        }
        if (payload.prompts_update) {
            prompts.clear();
            for (const prompt of payload.prompts_update) prompts.set(prompt.prompt_id, prompt);
            appliedCount += 1;
        }

        this.state = {
            ...this.state,
            tick: payload.to_tick,
            stepHash: payload.step_hash,
            schemaVersion: payload.schema_version,
            lastMsgType: "FRAME_DIFF",
            lastAppliedDiffCount: appliedCount,
            diffsAppliedTotal: this.state.diffsAppliedTotal + 1,
            worldMeta,
            inventory,
            regime,
            rooms,
            supervisors,
            events,
            prompts,
        };
        this.emit();
    }

    private emit(): void {
        for (const cb of this.subs) cb(this.state);
    }
}

function eventKey(ev: SimSimEvent): string {
    return `${ev.tick}:${ev.event_id}`;
}
