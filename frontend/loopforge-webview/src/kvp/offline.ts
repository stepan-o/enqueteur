// src/kvp/offline.ts
import type {
    FrameDiffPayload,
    FullSnapshotPayload,
    KernelHello,
    RenderSpec,
    RunAnchors,
    WorldStore,
} from "../state/worldStore";
import type { OverlayStore, UIOverlayEvent, PsychoFrame } from "../state/overlayStore";
import type { ViewerStore } from "../state/viewerStore";

type RecordPointer = {
    rel_path: string;
    msg_type: "FULL_SNAPSHOT" | "FRAME_DIFF" | string;
    tick?: number;
    from_tick?: number;
    to_tick?: number;
};

type OfflineManifest = {
    kvp_version: string;
    schema_version: string;
    run_anchors: RunAnchors;
    render_spec?: RenderSpec;
    available_start_tick?: number;
    available_end_tick?: number;
    keyframe_interval?: number;
    keyframe_ticks?: number[];
    snapshots: Record<string, RecordPointer>;
    diffs: { diffs_by_from_tick: Record<string, RecordPointer> };
    overlays?: Record<string, { rel_path: string; format: string; notes?: string | null }>;
};

export type OfflineRunOptions = {
    baseUrl: string;
    startTick?: number;
    endTick?: number;
    tickRateHz?: number;
    speed?: number;
    overlayStore?: OverlayStore;
    viewerStore?: ViewerStore;
};

export type OfflineRunHandle = {
    stop: () => void;
    pause: () => void;
    resume: () => void;
    setSpeed: (speed: number) => void;
    isPaused: () => boolean;
    seekToTick: (tick: number) => Promise<void>;
};

export async function startOfflineRun(store: WorldStore, opts: OfflineRunOptions): Promise<OfflineRunHandle> {
    const baseUrl = opts.baseUrl.replace(/\/+$/, "");
    const manifest = await fetchJson<OfflineManifest>(`${baseUrl}/manifest.kvp.json`);
    const overlayStore = opts.overlayStore;
    const viewerStore = opts.viewerStore;

    if (overlayStore && manifest.overlays) {
        await loadOverlayStreams(baseUrl, manifest.overlays, overlayStore);
    }

    store.setRunAnchors(manifest.run_anchors);
    if (manifest.render_spec) store.setRenderSpec(manifest.render_spec);

    const kernelHello: KernelHello = {
        engine_name: manifest.run_anchors.engine_name,
        engine_version: manifest.run_anchors.engine_version,
        schema_version: manifest.run_anchors.schema_version,
        world_id: manifest.run_anchors.world_id,
        run_id: manifest.run_anchors.run_id,
        seed: manifest.run_anchors.seed,
        tick_rate_hz: manifest.run_anchors.tick_rate_hz,
        time_origin_ms: manifest.run_anchors.time_origin_ms,
    };
    store.setKernelHello(kernelHello);

    const snapshotTicks = Object.keys(manifest.snapshots).map((k) => Number(k)).sort((a, b) => a - b);
    if (snapshotTicks.length === 0) {
        throw new Error("Manifest contains no snapshots");
    }

    const startTick = opts.startTick ?? manifest.available_start_tick ?? snapshotTicks[0];
    const endTick = opts.endTick ?? manifest.available_end_tick ?? snapshotTicks[snapshotTicks.length - 1];
    if (viewerStore) viewerStore.setPlaybackWindow(startTick, endTick);

    const snapshotTick = findLatestSnapshot(snapshotTicks, startTick);
    const snapPtr = manifest.snapshots[String(snapshotTick)];
    if (!snapPtr) {
        throw new Error(`Snapshot pointer missing for tick ${snapshotTick}`);
    }

    const snapPayload = await loadPayload<FullSnapshotPayload>(baseUrl, snapPtr.rel_path);
    store.applySnapshot(snapPayload);
    if (overlayStore) overlayStore.setTick(snapPayload.tick);

    let currentTick = snapPayload.tick;

    if (currentTick < startTick) {
        currentTick = await fastForward(store, baseUrl, manifest, currentTick, startTick, overlayStore);
    }

    const tickRateHz = opts.tickRateHz ?? manifest.run_anchors.tick_rate_hz ?? 30;
    let speed = opts.speed && opts.speed > 0 ? opts.speed : 1;
    let intervalMs = Math.max(5, Math.floor(1000 / (tickRateHz * speed)));

    let stopped = false;
    let inFlight = false;
    let paused = false;
    let seeking = false;
    let timer: number | null = null;

    const startTimer = () => {
        if (timer !== null) window.clearInterval(timer);
        if (paused || stopped) return;
        timer = window.setInterval(() => {
            if (stopped || inFlight || paused || seeking) return;
            inFlight = true;
            void stepOnce()
                .catch((err: unknown) => {
                    const msg = err instanceof Error ? err.message : String(err);
                    store.markDesync(`Offline playback error: ${msg}`);
                    stopped = true;
                    if (timer !== null) window.clearInterval(timer);
                })
                .finally(() => {
                    inFlight = false;
                });
        }, intervalMs);
    };

    startTimer();

    async function stepOnce(): Promise<void> {
        if (currentTick >= endTick) {
            if (timer !== null) window.clearInterval(timer);
            return;
        }

        const ptr = manifest.diffs.diffs_by_from_tick[String(currentTick)];
        if (!ptr) {
            throw new Error(`Missing diff pointer for tick ${currentTick}`);
        }

        const diffPayload = await loadPayload<FrameDiffPayload>(baseUrl, ptr.rel_path);
        store.applyDiff(diffPayload);
        currentTick = diffPayload.to_tick;
        if (overlayStore) overlayStore.setTick(currentTick);
    }

    return {
        stop: () => {
            stopped = true;
            if (timer !== null) window.clearInterval(timer);
        },
        pause: () => {
            paused = true;
            if (timer !== null) window.clearInterval(timer);
        },
        resume: () => {
            if (stopped) return;
            paused = false;
            startTimer();
        },
        setSpeed: (nextSpeed: number) => {
            if (!Number.isFinite(nextSpeed) || nextSpeed <= 0) return;
            speed = nextSpeed;
            intervalMs = Math.max(5, Math.floor(1000 / (tickRateHz * speed)));
            startTimer();
        },
        isPaused: () => paused,
        seekToTick: async (targetTick: number) => {
            if (!Number.isFinite(targetTick)) return;
            const clamped = Math.max(startTick, Math.min(endTick, Math.floor(targetTick)));
            const wasPaused = paused;
            paused = true;
            seeking = true;
            if (timer !== null) window.clearInterval(timer);

            while (inFlight) {
                await new Promise((r) => setTimeout(r, 5));
            }

            const snapTick = findLatestSnapshot(snapshotTicks, clamped);
            const snapPtr = manifest.snapshots[String(snapTick)];
            if (!snapPtr) {
                seeking = false;
                return;
            }
            const snapPayload = await loadPayload<FullSnapshotPayload>(baseUrl, snapPtr.rel_path);
            store.applySnapshot(snapPayload);
            if (overlayStore) overlayStore.setTick(snapPayload.tick);
            currentTick = snapPayload.tick;

            if (currentTick < clamped) {
                currentTick = await fastForward(store, baseUrl, manifest, currentTick, clamped, overlayStore);
            }

            seeking = false;
            if (!wasPaused) {
                paused = false;
                startTimer();
            }
        },
    };
}

function findLatestSnapshot(ticks: number[], target: number): number {
    let latest = ticks[0];
    for (const t of ticks) {
        if (t <= target) latest = t;
        else break;
    }
    return latest;
}

async function fastForward(
    store: WorldStore,
    baseUrl: string,
    manifest: OfflineManifest,
    fromTick: number,
    toTick: number,
    overlayStore?: OverlayStore
): Promise<number> {
    let current = fromTick;
    while (current < toTick) {
        const ptr = manifest.diffs.diffs_by_from_tick[String(current)];
        if (!ptr) {
            throw new Error(`Missing diff pointer for tick ${current}`);
        }
        const diffPayload = await loadPayload<FrameDiffPayload>(baseUrl, ptr.rel_path);
        store.applyDiff(diffPayload);
        current = diffPayload.to_tick;
        if (overlayStore) overlayStore.setTick(current);
    }
    return current;
}

async function loadOverlayStreams(
    baseUrl: string,
    overlays: Record<string, { rel_path: string; format: string; notes?: string | null }>,
    store: OverlayStore
): Promise<void> {
    const entries = Object.values(overlays);
    for (const entry of entries) {
        if (!entry?.rel_path) continue;
        const url = `${baseUrl}/${entry.rel_path}`;
        try {
            const text = await fetchText(url);
            const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
            for (const line of lines) {
                let env: any;
                try {
                    env = JSON.parse(line);
                } catch {
                    continue;
                }
                const msgType = env?.msg_type;
                const payload = env?.payload;
                if (msgType === "X_UI_EVENT_BATCH" && payload) {
                    const events = (payload.events ?? []) as UIOverlayEvent[];
                    store.ingestUiEventBatch({
                        start_tick: payload.start_tick ?? 0,
                        end_tick: payload.end_tick ?? 0,
                        events,
                    });
                } else if (msgType === "X_PSYCHO_FRAME" && payload) {
                    store.ingestPsychoFrame(payload as PsychoFrame);
                }
            }
        } catch (err) {
            console.warn("[webview] overlay load failed", url, err);
        }
    }
}

async function loadPayload<T>(baseUrl: string, relPath: string): Promise<T> {
    const envelope = await fetchJson<{ payload: T }>(`${baseUrl}/${relPath}`);
    return envelope.payload;
}

async function fetchJson<T>(url: string): Promise<T> {
    const res = await fetch(url);
    if (!res.ok) {
        throw new Error(`Fetch failed (${res.status}) for ${url}`);
    }
    return (await res.json()) as T;
}

async function fetchText(url: string): Promise<string> {
    const res = await fetch(url);
    if (!res.ok) {
        throw new Error(`Fetch failed (${res.status}) for ${url}`);
    }
    return res.text();
}
