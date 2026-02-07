// src/kvp/offline.ts
import type {
    FrameDiffPayload,
    FullSnapshotPayload,
    KernelHello,
    RenderSpec,
    RunAnchors,
    WorldStore,
} from "../state/worldStore";

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
};

export type OfflineRunOptions = {
    baseUrl: string;
    startTick?: number;
    endTick?: number;
    tickRateHz?: number;
    speed?: number;
};

export type OfflineRunHandle = {
    stop: () => void;
};

export async function startOfflineRun(store: WorldStore, opts: OfflineRunOptions): Promise<OfflineRunHandle> {
    const baseUrl = opts.baseUrl.replace(/\/+$/, "");
    const manifest = await fetchJson<OfflineManifest>(`${baseUrl}/manifest.kvp.json`);

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

    const snapshotTick = findLatestSnapshot(snapshotTicks, startTick);
    const snapPtr = manifest.snapshots[String(snapshotTick)];
    if (!snapPtr) {
        throw new Error(`Snapshot pointer missing for tick ${snapshotTick}`);
    }

    const snapPayload = await loadPayload<FullSnapshotPayload>(baseUrl, snapPtr.rel_path);
    store.applySnapshot(snapPayload);

    let currentTick = snapPayload.tick;

    if (currentTick < startTick) {
        currentTick = await fastForward(store, baseUrl, manifest, currentTick, startTick);
    }

    const tickRateHz = opts.tickRateHz ?? manifest.run_anchors.tick_rate_hz ?? 30;
    const speed = opts.speed && opts.speed > 0 ? opts.speed : 1;
    const intervalMs = Math.max(5, Math.floor(1000 / (tickRateHz * speed)));

    let stopped = false;
    let inFlight = false;

    const timer = window.setInterval(() => {
        if (stopped || inFlight) return;
        inFlight = true;
        void stepOnce()
            .catch((err: unknown) => {
                const msg = err instanceof Error ? err.message : String(err);
                store.markDesync(`Offline playback error: ${msg}`);
                stopped = true;
                window.clearInterval(timer);
            })
            .finally(() => {
                inFlight = false;
            });
    }, intervalMs);

    async function stepOnce(): Promise<void> {
        if (currentTick >= endTick) {
            window.clearInterval(timer);
            return;
        }

        const ptr = manifest.diffs.diffs_by_from_tick[String(currentTick)];
        if (!ptr) {
            throw new Error(`Missing diff pointer for tick ${currentTick}`);
        }

        const diffPayload = await loadPayload<FrameDiffPayload>(baseUrl, ptr.rel_path);
        store.applyDiff(diffPayload);
        currentTick = diffPayload.to_tick;
    }

    return {
        stop: () => {
            stopped = true;
            window.clearInterval(timer);
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
    toTick: number
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
    }
    return current;
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
