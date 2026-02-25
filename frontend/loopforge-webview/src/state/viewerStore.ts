// src/state/viewerStore.ts

export type LiveKernelKind = "sim4" | "sim_sim";

export type ViewerState = {
    playbackStartTick: number;
    playbackEndTick: number;
    keyframeTicks: number[];
    highlights: Array<{ tick: number; label: string }>;
    liveKernelKind: LiveKernelKind;
};

export type ViewerStoreSubscriber = (s: ViewerState) => void;

export class ViewerStore {
    private state: ViewerState;
    private readonly subs = new Set<ViewerStoreSubscriber>();

    constructor() {
        this.state = {
            playbackStartTick: 0,
            playbackEndTick: 0,
            keyframeTicks: [],
            highlights: [],
            liveKernelKind: "sim4",
        };
    }

    subscribe(cb: ViewerStoreSubscriber): () => void {
        this.subs.add(cb);
        cb(this.state);
        return () => this.subs.delete(cb);
    }

    getState(): ViewerState {
        return this.state;
    }

    setPlaybackWindow(startTick: number, endTick: number): void {
        if (!Number.isFinite(startTick) || !Number.isFinite(endTick)) return;
        const start = Math.max(0, Math.floor(startTick));
        const end = Math.max(start, Math.floor(endTick));
        this.state = { ...this.state, playbackStartTick: start, playbackEndTick: end };
        this.emit();
    }

    setKeyframes(ticks: number[]): void {
        const filtered = ticks
            .filter((t) => Number.isFinite(t))
            .map((t) => Math.floor(t))
            .filter((t) => t >= 0);
        this.state = { ...this.state, keyframeTicks: filtered };
        this.emit();
    }

    setHighlights(entries: Array<{ tick: number; label: string }>): void {
        const filtered = entries
            .filter((h) => Number.isFinite(h.tick))
            .map((h) => ({ tick: Math.floor(h.tick), label: h.label ?? `Tick ${h.tick}` }))
            .filter((h) => h.tick >= 0);
        this.state = { ...this.state, highlights: filtered };
        this.emit();
    }

    setLiveKernelKind(kind: LiveKernelKind): void {
        if (this.state.liveKernelKind === kind) return;
        this.state = { ...this.state, liveKernelKind: kind };
        this.emit();
    }

    private emit(): void {
        for (const cb of this.subs) cb(this.state);
    }
}
