// src/state/viewerStore.ts

export type ViewerState = {
    playbackStartTick: number;
    playbackEndTick: number;
};

export type ViewerStoreSubscriber = (s: ViewerState) => void;

export class ViewerStore {
    private state: ViewerState;
    private readonly subs = new Set<ViewerStoreSubscriber>();

    constructor() {
        this.state = {
            playbackStartTick: 0,
            playbackEndTick: 0,
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

    private emit(): void {
        for (const cb of this.subs) cb(this.state);
    }
}

