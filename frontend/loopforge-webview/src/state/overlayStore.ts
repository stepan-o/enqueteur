// src/state/overlayStore.ts

export type UIOverlayEvent = {
    tick: number;
    event_id: string | number;
    kind: string;
    data: Record<string, unknown>;
};

export type PsychoFrame = {
    tick: number;
    nodes: Array<Record<string, unknown>>;
    edges: Array<Record<string, unknown>>;
};

export type OverlayState = {
    currentTick: number;
    recentEvents: UIOverlayEvent[];
    eventsAtTick: UIOverlayEvent[];
    eventsByTick: Map<number, UIOverlayEvent[]>;
    psychoByTick: Map<number, PsychoFrame>;
};

export type OverlayStoreSubscriber = (s: OverlayState) => void;

const MAX_RECENT = 8;
const MAX_ADVANCE_SCAN = 240;

export class OverlayStore {
    private state: OverlayState;
    private readonly subs = new Set<OverlayStoreSubscriber>();

    constructor() {
        this.state = {
            currentTick: 0,
            recentEvents: [],
            eventsAtTick: [],
            eventsByTick: new Map(),
            psychoByTick: new Map(),
        };
    }

    subscribe(cb: OverlayStoreSubscriber): () => void {
        this.subs.add(cb);
        cb(this.state);
        return () => this.subs.delete(cb);
    }

    getState(): OverlayState {
        return this.state;
    }

    ingestUiEventBatch(batch: { start_tick: number; end_tick: number; events: UIOverlayEvent[] }): void {
        const events = batch.events ?? [];
        for (const ev of events) {
            const list = this.state.eventsByTick.get(ev.tick) ?? [];
            list.push(ev);
            this.state.eventsByTick.set(ev.tick, list);
        }
        this.emit();
    }

    ingestPsychoFrame(frame: PsychoFrame): void {
        this.state.psychoByTick.set(frame.tick, frame);
        this.emit();
    }

    setTick(tick: number): void {
        const prev = this.state.currentTick;
        if (tick === prev) return;

        let recent = this.state.recentEvents.slice();
        if (tick < prev) {
            recent = [];
        }

        let newEvents: UIOverlayEvent[] = [];
        const delta = tick - prev;
        if (delta > 1 && delta <= MAX_ADVANCE_SCAN) {
            for (let t = prev + 1; t <= tick; t += 1) {
                const events = this.state.eventsByTick.get(t) ?? [];
                if (events.length) newEvents = newEvents.concat(events);
            }
        } else {
            newEvents = this.state.eventsByTick.get(tick) ?? [];
        }

        if (newEvents.length) {
            recent = recent.concat(newEvents);
            if (recent.length > MAX_RECENT) {
                recent = recent.slice(recent.length - MAX_RECENT);
            }
        }

        const eventsAtTick = this.state.eventsByTick.get(tick) ?? [];

        this.state = {
            ...this.state,
            currentTick: tick,
            recentEvents: recent,
            eventsAtTick,
        };
        this.emit();
    }

    private emit(): void {
        for (const cb of this.subs) cb(this.state);
    }
}

