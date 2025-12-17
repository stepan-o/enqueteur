// src/state/worldStore.ts
/**
 * WorldStore (WEBVIEW-0001)
 * -----------------------------------------------------------------------------
 * The viewer's in-memory mirror of kernel truth.
 * - Accepts FULL_SNAPSHOT baseline
 * - Applies FRAME_DIFF incrementally
 * - Detects basic desync conditions (baseline mismatch, bad ordering)
 *
 * Non-goals:
 * - No simulation logic
 * - No derived inference beyond display-friendly indexing
 * - No persistence (replay caching comes later)
 */

export type Tick = number;

/* ---------------------------------------
 * Minimal payload shapes (v0.1 placeholders)
 * Replace with generated KVP types later.
 * ------------------------------------- */

export type KernelHello = {
    engine_name: string;
    engine_version: string;
    schema_version: string;
    world_id: string;
    run_id: string;
    seed: number;
    tick_rate_hz: number;
};

export type Vec2 = { x: number; y: number };

export type RoomSnapshot = {
    room_id: number;
    name?: string;
    zone_id?: number;
    bounds?: { x: number; y: number; w: number; h: number };
    occupancy?: number;
    tension?: number;
};

export type AgentSnapshot = {
    agent_id: number;
    room_id: number | null;
    pos: Vec2;
    facing_deg?: number;
    public_state?: {
        label?: string;
        mood?: number;
        energy?: number;
        speaking?: boolean;
        emote?: string | null;
    };
};

export type NarrativeFragment = {
    entity_id: number;
    kind: "DIALOGUE" | "INNER_MONOLOGUE" | "THOUGHT_TAG" | string;
    text: string;
    ttl_ticks?: number;
    nondeterministic?: boolean;
};

export type FullSnapshot = {
    schema_version: string;
    tick: Tick;
    step_hash: string;

    world?: { rooms?: RoomSnapshot[] };
    agents?: AgentSnapshot[];
    narrative_fragments?: NarrativeFragment[];
};

export type AgentMove = {
    agent_id: number;
    from_room_id: number | null;
    to_room_id: number | null;
    from_pos: Vec2;
    to_pos: Vec2;
};

export type FrameDiff = {
    schema_version: string;
    from_tick: Tick;
    to_tick: Tick;
    step_hash: string;

    diff: {
        // Phase 1 policy: replace-lists (safe + simple)
        room_replacements?: RoomSnapshot[];
        narrative_replacements?: NarrativeFragment[];

        // Incremental agent updates
        agent_moves?: AgentMove[];
        agent_spawns?: AgentSnapshot[];
        agent_despawns?: number[];

        // Events/items omitted for skeleton; add later
    };
};

/* ---------------------------------------
 * Viewer State
 * ------------------------------------- */

export type WorldState = {
    // Connection/session metadata
    connected: boolean;
    kernelHello?: KernelHello;

    // Current sim time
    tick: Tick;
    stepHash: string;

    // Canonical indices for fast lookup
    rooms: Map<number, RoomSnapshot>;
    agents: Map<number, AgentSnapshot>;

    // Narrative fragments are replace-lists; we index by a stable key.
    narrative: Map<string, NarrativeFragment>;

    // Diagnostics
    desynced: boolean;
    desyncReason?: string;
};

export class WorldStore {
    public state: WorldState;

    private listeners = new Set<(s: WorldState) => void>();

    constructor() {
        this.state = {
            connected: false,
            tick: 0,
            stepHash: "",
            rooms: new Map(),
            agents: new Map(),
            narrative: new Map(),
            desynced: false,
        };
    }

    subscribe(fn: (s: WorldState) => void): () => void {
        this.listeners.add(fn);
        fn(this.state);
        return () => this.listeners.delete(fn);
    }

    private emit(): void {
        for (const fn of this.listeners) fn(this.state);
    }

    /* ---------------------------------------
     * Session / Connection
     * ------------------------------------- */

    setConnected(connected: boolean): void {
        this.state.connected = connected;

        // If disconnected, we do NOT clear state automatically.
        // Viewer can decide whether to keep last frame visible.
        this.emit();
    }

    setKernelHello(hello: KernelHello): void {
        this.state.kernelHello = hello;
        this.emit();
    }

    /* ---------------------------------------
     * Apply FULL_SNAPSHOT (baseline)
     * ------------------------------------- */

    applySnapshot(s: FullSnapshot): void {
        // A snapshot is authoritative baseline; it resets desync flags.
        this.state.desynced = false;
        this.state.desyncReason = undefined;

        this.state.tick = s.tick ?? 0;
        this.state.stepHash = s.step_hash ?? "";

        // Replace rooms
        this.state.rooms.clear();
        const rooms = s.world?.rooms ?? [];
        for (const r of rooms) {
            if (typeof r?.room_id !== "number") continue;
            this.state.rooms.set(r.room_id, r);
        }

        // Replace agents
        this.state.agents.clear();
        const agents = s.agents ?? [];
        for (const a of agents) {
            if (typeof a?.agent_id !== "number") continue;
            this.state.agents.set(a.agent_id, sanitizeAgent(a));
        }

        // Replace narrative fragments
        this.state.narrative.clear();
        const frags = s.narrative_fragments ?? [];
        for (const n of frags) {
            this.state.narrative.set(narrativeKey(n), n);
        }

        this.emit();
    }

    /* ---------------------------------------
     * Apply FRAME_DIFF (incremental)
     * ------------------------------------- */

    applyDiff(d: FrameDiff): void {
        if (this.state.desynced) return;

        // Baseline must match current tick
        if (d.from_tick !== this.state.tick) {
            this.markDesync(`Diff baseline mismatch: expected from_tick=${this.state.tick}, got ${d.from_tick}`);
            return;
        }

        // Tick must advance
        if (typeof d.to_tick !== "number" || d.to_tick < d.from_tick) {
            this.markDesync(`Invalid diff ticks: from=${d.from_tick} to=${d.to_tick}`);
            return;
        }

        // Phase 1: replace rooms/events/narrative as lists
        const roomRepl = d.diff.room_replacements ?? [];
        for (const r of roomRepl) {
            if (typeof r?.room_id !== "number") continue;
            this.state.rooms.set(r.room_id, r);
        }

        // Agents: despawn → spawn → move
        for (const id of d.diff.agent_despawns ?? []) {
            this.state.agents.delete(id);
        }

        for (const a of d.diff.agent_spawns ?? []) {
            if (typeof a?.agent_id !== "number") continue;
            this.state.agents.set(a.agent_id, sanitizeAgent(a));
        }

        for (const m of d.diff.agent_moves ?? []) {
            const a = this.state.agents.get(m.agent_id);
            if (!a) continue;

            a.room_id = m.to_room_id;
            a.pos = { x: m.to_pos.x, y: m.to_pos.y };

            this.state.agents.set(a.agent_id, a);
        }

        // Narrative replace-list policy
        if (d.diff.narrative_replacements) {
            this.state.narrative.clear();
            for (const n of d.diff.narrative_replacements) {
                this.state.narrative.set(narrativeKey(n), n);
            }
        }

        // Advance time
        this.state.tick = d.to_tick;
        this.state.stepHash = d.step_hash ?? this.state.stepHash;

        this.emit();
    }

    /* ---------------------------------------
     * Diagnostics
     * ------------------------------------- */

    markDesync(reason: string): void {
        this.state.desynced = true;
        this.state.desyncReason = reason;
        this.emit();
    }
}

/* ---------------------------------------
 * Helpers
 * ------------------------------------- */

function sanitizeAgent(a: AgentSnapshot): AgentSnapshot {
    // Ensure required fields exist for renderer.
    const pos = a.pos ?? { x: 0, y: 0 };
    return {
        agent_id: a.agent_id,
        room_id: a.room_id ?? null,
        pos: { x: pos.x ?? 0, y: pos.y ?? 0 },
        facing_deg: a.facing_deg ?? 0,
        public_state: {
            label: a.public_state?.label ?? `Agent ${a.agent_id}`,
            mood: a.public_state?.mood ?? 0,
            energy: a.public_state?.energy ?? 0,
            speaking: a.public_state?.speaking ?? false,
            emote: a.public_state?.emote ?? null,
        },
    };
}

function narrativeKey(n: NarrativeFragment): string {
    // Stable-ish key for UI indexing in Phase 1. Replace with fragment_id later.
    return `${n.entity_id}:${n.kind}:${n.text}`;
}
