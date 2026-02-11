// src/app/boot.ts
import { WorldStore } from "../state/worldStore";
import { OverlayStore } from "../state/overlayStore";
import { ViewerStore } from "../state/viewerStore";
import { KvpClient } from "../kvp/client";
import { startOfflineRun } from "../kvp/offline";
import type { OfflineRunHandle } from "../kvp/offline";
import { PixiScene } from "../render/pixiScene";
import { mountHud } from "../ui/hud";
import { mountDevControls } from "../ui/devControls";
import { injectMockSnapshot } from "../debug/mockKernel";

/**
 * Boot the Loopforge Web Viewer (WEBVIEW-0001).
 * - Protocol-first (KVP-0001)
 * - No simulation logic
 * - Web viewer is a client: snapshot + diff → render
 */
export type BootMode = "live" | "offline";

export type BootOpts = {
    mountEl: HTMLElement;
    wsUrl?: string;
    offlineBaseUrl?: string;
    mode?: BootMode;
};

export function boot(opts: BootOpts): void {
    const store = new WorldStore();
    const overlayStore = new OverlayStore();
    const viewerStore = new ViewerStore();

    // Mount container should be positioning context for HUD overlays.
    opts.mountEl.style.position = "relative";
    opts.mountEl.style.width = "100%";
    opts.mountEl.style.height = "100%";

    // Renderer (PixiJS)
    const scene = new PixiScene(opts.mountEl);

    // HUD (DOM overlay)
    const hud = mountHud(store, overlayStore);
    opts.mountEl.appendChild(hud);

    overlayStore.subscribe((o) => {
        scene.ingestOverlayEvents(o.eventsAtTick);
    });

    // --- DEBUG: prove canvas exists + has size (Pixi v8 async init) -----------
    const debugCanvasProbe = () => {
        const canvas = opts.mountEl.querySelector("canvas") as HTMLCanvasElement | null;
        const rect = canvas?.getBoundingClientRect();
        console.debug("[webview] canvas probe", {
            hasCanvas: !!canvas,
            rect: rect ? { w: Math.round(rect.width), h: Math.round(rect.height) } : null,
        });
    };
    // Probe immediately and again after a tick, since Pixi init is async.
    debugCanvasProbe();
    setTimeout(debugCanvasProbe, 0);
    setTimeout(debugCanvasProbe, 250);

    // Render on state changes (simple + correct; later you can batch)
    store.subscribe((s) => {
        console.debug("[webview] state", {
            tick: s.tick,
            rooms: s.rooms.size,
            agents: s.agents.size,
            items: s.items.size,
            desynced: s.desynced,
            reason: s.desyncReason ?? null,
            stepHash: s.stepHash ?? null,
        });

        scene.renderFromState(s);
    });

    const env = (import.meta as any).env ?? {};
    const mode = (opts.mode ?? env.VITE_WEBVIEW_MODE ?? "offline") as BootMode;
    let offlineHandle: OfflineRunHandle | null = null;
    let offlineBaseUrl = opts.offlineBaseUrl ?? env.VITE_WEBVIEW_RUN_BASE ?? "/demo/kvp_demo_1min";
    let offlineSpeed = parseFloat(env.VITE_WEBVIEW_SPEED ?? "1");

    const devControls = mountDevControls({
        store,
        viewerStore,
        onFloorChange: (floor) => scene.setFloorFilter(floor),
        onCameraModeChange: (mode) => scene.setCameraMode(mode),
        onRotate: (delta) => scene.rotateView(delta),
        onPlaybackToggle: (paused) => {
            if (mode !== "offline") return;
            if (!offlineHandle) return;
            if (paused) offlineHandle.pause();
            else offlineHandle.resume();
        },
        onSpeedChange: (speed) => {
            offlineSpeed = speed;
            if (mode !== "offline") return;
            if (!offlineHandle) return;
            offlineHandle.setSpeed(speed);
        },
        onSeek: (tick) => {
            if (mode !== "offline") return;
            if (!offlineHandle) return;
            void offlineHandle.seekToTick(tick);
        },
        onRestart: () => {
            if (mode !== "offline") return;
            if (offlineHandle) offlineHandle.stop();
            store.clearDesync();
            startOfflineRun(store, { baseUrl: offlineBaseUrl, speed: offlineSpeed, overlayStore, viewerStore })
                .then((handle) => {
                    offlineHandle = handle;
                })
                .catch((err: unknown) => {
                    const msg = err instanceof Error ? err.message : String(err);
                    store.markDesync(`Offline restart failed: ${msg}`);
                });
        },
    });
    opts.mountEl.appendChild(devControls);

    if (mode === "offline") {
        const baseUrl = offlineBaseUrl;
        const speed = offlineSpeed;

        store.setMode("offline");
        store.setConnected(true);

        startOfflineRun(store, { baseUrl, speed, overlayStore, viewerStore })
            .then((handle) => {
                console.info("[webview] offline run ready:", baseUrl);
                offlineHandle = handle;
            })
            .catch((err: unknown) => {
                const msg = err instanceof Error ? err.message : String(err);
                console.error("[webview] offline run failed:", msg);
                store.markDesync(`Offline load failed: ${msg}`);
            });

        return;
    }

    store.setMode("live");

    // KVP client
    const client = new KvpClient(store, {
        url: opts.wsUrl ?? env.VITE_KVP_WS_URL ?? "ws://localhost:7777/kvp",
        viewerName: "loopforge-webview-pixi",
        viewerVersion: "0.1.0",
        supportedSchemaVersions: ["1"],
        defaultSubscribe: {
            stream: "LIVE",
            channels: ["WORLD", "AGENTS", "ITEMS", "EVENTS", "DEBUG"],
            diff_policy: "DIFF_ONLY",
            snapshot_policy: "ON_JOIN",
            compression: "NONE",
        },
    });

    // Desync recovery hook (banner click → request fresh snapshot)
    scene.onRequestFreshSnapshot(() => {
        console.warn("[webview] desync banner: requesting fresh snapshot");
        client.requestFreshSnapshot();
    });

    // DEV: render without a kernel
    if (import.meta.env.DEV) {
        const useMock = String(env.VITE_WEBVIEW_MOCK ?? "") === "1";
        if (useMock) {
            console.info("[webview] DEV mode: injecting mock snapshot");
            injectMockSnapshot(store);
        }

        // --- DEBUG: optionally run webview without WS to avoid overwriting mock
        // Set VITE_WEBVIEW_DISABLE_WS=1 to keep the mock state on screen.
        const disableWs = String(env.VITE_WEBVIEW_DISABLE_WS ?? "") === "1";
        if (disableWs) {
            console.info("[webview] WS disabled (VITE_WEBVIEW_DISABLE_WS=1). Skipping client.connect().");
            return;
        }
    }

    // Connect!
    console.info("[webview] connecting WS:", opts.wsUrl ?? env.VITE_KVP_WS_URL ?? "ws://localhost:7777/kvp");
    client.connect();
}
