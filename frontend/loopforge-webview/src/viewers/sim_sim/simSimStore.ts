import type { KernelHello } from "../../state/worldStore";

export const SIM_SIM_SCHEMA_VERSION = "sim_sim_1";

export type SimSimRoom = {
    room_id: number;
    label?: string;
    occupants?: number[];
    bounds?: { min_x: number; min_y: number; max_x: number; max_y: number } | null;
    zone?: string | null;
    highlight?: boolean | null;
};

export type SimSimAgent = {
    agent_id: number;
    room_id: number;
    transform?: { room_id: number; x: number; y: number } | null;
};

export type SimSimEvent = {
    tick: number;
    event_id: number;
    origin?: string;
    payload?: Record<string, unknown>;
};

export type SimSimWorld = Record<string, unknown>;

export type SimSimSnapshotPayload = {
    schema_version: string;
    tick: number;
    state: {
        rooms?: SimSimRoom[];
        agents?: SimSimAgent[];
        events?: SimSimEvent[];
        world?: SimSimWorld;
    };
    step_hash: string;
};

export type SimSimDiffOp =
    | { op: "SET_WORLD"; world: SimSimWorld }
    | { op: "CLEAR_WORLD" }
    | { op: "UPSERT_ROOM"; room: SimSimRoom }
    | { op: "REMOVE_ROOM"; room_id: number }
    | { op: "UPSERT_AGENT"; agent: SimSimAgent }
    | { op: "REMOVE_AGENT"; agent_id: number }
    | { op: "UPSERT_EVENT"; event: SimSimEvent }
    | { op: "REMOVE_EVENT"; event_key: { tick: number; event_id: number } };

export type SimSimFrameDiffPayload = {
    schema_version: string;
    from_tick: number;
    to_tick: number;
    prev_step_hash?: string | null;
    ops: SimSimDiffOp[];
    step_hash: string;
};

export type SimSimViewerState = {
    tick: number;
    stepHash?: string;
    kernelHello?: KernelHello;
    world: SimSimWorld | null;
    rooms: Map<number, SimSimRoom>;
    agents: Map<number, SimSimAgent>;
    events: Map<string, SimSimEvent>;
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
            kernelHello: undefined,
            world: null,
            rooms: new Map(),
            agents: new Map(),
            events: new Map(),
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
        this.state = { ...this.state, kernelHello: hello };
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

        const agents = new Map<number, SimSimAgent>();
        for (const agent of payload.state.agents ?? []) agents.set(agent.agent_id, agent);

        const events = new Map<string, SimSimEvent>();
        for (const ev of payload.state.events ?? []) events.set(eventKey(ev), ev);

        this.state = {
            ...this.state,
            tick: payload.tick,
            stepHash: payload.step_hash,
            world: payload.state.world ?? null,
            rooms,
            agents,
            events,
            desynced: false,
            desyncReason: undefined,
        };
        this.emit();
    }

    applyDiff(payload: SimSimFrameDiffPayload): void {
        if (this.state.desynced) return;
        if (!payload || !Array.isArray(payload.ops)) {
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
        if (this.state.tick && payload.from_tick !== this.state.tick) {
            this.markDesync(`sim_sim tick mismatch (expected ${this.state.tick}, got ${payload.from_tick})`);
            return;
        }

        const rooms = new Map(this.state.rooms);
        const agents = new Map(this.state.agents);
        const events = new Map(this.state.events);
        let world = this.state.world;

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
                case "UPSERT_EVENT":
                    events.set(eventKey(op.event), op.event);
                    break;
                case "REMOVE_EVENT":
                    events.delete(`${op.event_key.tick}:${op.event_key.event_id}`);
                    break;
                default:
                    this.markDesync(`Unknown sim_sim diff op: ${(op as { op?: string }).op ?? "?"}`);
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
            events,
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

