// src/app/boot.ts
import { WorldStore } from "../state/worldStore";
import { OverlayStore } from "../state/overlayStore";
import { ViewerStore } from "../state/viewerStore";
import type { LiveKernelKind } from "../state/viewerStore";
import { KvpClient } from "../kvp/client";
import { startOfflineRun } from "../kvp/offline";
import type { OfflineRunHandle } from "../kvp/offline";
import { PixiScene } from "../render/pixiScene";
import { mountHud } from "../ui/hud";
import { mountDevControls } from "../ui/devControls";
import { mountInspectPanel } from "../ui/inspectPanel";
import { mountTimeLighting } from "../ui/timeLighting";
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
    // Backward-compatible alias for sim4 live endpoint.
    wsUrl?: string;
    sim4WsUrl?: string;
    simSimWsUrl?: string;
    offlineBaseUrl?: string;
    mode?: BootMode;
    autoStart?: boolean;
};

export type LiveStartOpts = {
    kernelKind?: LiveKernelKind;
    wsUrl?: string;
};

export type ViewerHandle = {
    startOffline: (baseUrl?: string, speed?: number) => Promise<void>;
    startLive: (opts?: LiveStartOpts) => void;
    stop: () => void;
    setVisible: (visible: boolean) => void;
    setDevControlsVisible: (visible: boolean) => void;
    setHudVisible: (visible: boolean) => void;
};

export function boot(opts: BootOpts): ViewerHandle {
    const store = new WorldStore();
    const overlayStore = new OverlayStore();
    const viewerStore = new ViewerStore();

    // Mount container should be positioning context for HUD overlays.
    opts.mountEl.style.position = "relative";
    opts.mountEl.style.width = "100%";
    opts.mountEl.style.height = "100%";

    // Renderer (PixiJS)
    const scene = new PixiScene(opts.mountEl);

    const timeLighting = mountTimeLighting(opts.mountEl);

    // HUD (DOM overlay)
    const hud = mountHud(store, overlayStore);
    opts.mountEl.appendChild(hud);

    // Inspector (DOM overlay)
    const inspector = mountInspectPanel(store);
    opts.mountEl.appendChild(inspector.root);

    overlayStore.subscribe((o) => {
        scene.ingestOverlayEvents(o.eventsAtTick);
    });

    scene.onInspectSelection((sel) => inspector.setSelection(sel));

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

        timeLighting.update(s.world ?? null);
        scene.renderFromState(s);
    });

    const env = (import.meta as any).env ?? {};
    const mode = (opts.mode ?? env.VITE_WEBVIEW_MODE ?? "offline") as BootMode;
    const autoStart = opts.autoStart ?? true;
    let offlineHandle: OfflineRunHandle | null = null;
    let offlineBaseUrl = opts.offlineBaseUrl ?? env.VITE_WEBVIEW_RUN_BASE ?? "/demo/kvp_demo_1min";
    let offlineSpeed = parseFloat(env.VITE_WEBVIEW_SPEED ?? "1");
    let currentMode: BootMode = mode;
    let client: KvpClient | null = null;
    let activeLiveWsUrl: string | null = null;

    const resolveLiveWsUrl = (kernelKind: LiveKernelKind): string => {
        if (kernelKind === "sim_sim") {
            return opts.simSimWsUrl ?? env.VITE_KVP_WS_URL_SIM_SIM ?? "ws://localhost:7777/kvp";
        }
        return opts.sim4WsUrl ?? opts.wsUrl ?? env.VITE_KVP_WS_URL_SIM4 ?? env.VITE_KVP_WS_URL ?? "ws://localhost:7777/kvp";
    };

    const ensureLiveClient = (wsUrl: string): KvpClient => {
        if (client && activeLiveWsUrl === wsUrl) return client;
        if (client) client.disconnect();
        client = new KvpClient(store, {
            url: wsUrl,
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
        activeLiveWsUrl = wsUrl;
        scene.onRequestFreshSnapshot(() => {
            console.warn("[webview] desync banner: requesting fresh snapshot");
            client?.requestFreshSnapshot();
        });
        return client;
    };

    const devControls = mountDevControls({
        store,
        viewerStore,
        onFloorChange: (floor) => scene.setFloorFilter(floor),
        onCameraModeChange: (mode) => scene.setCameraMode(mode),
        onRotate: (delta) => scene.rotateView(delta),
        onPlaybackToggle: (paused) => {
            if (currentMode !== "offline") return;
            if (!offlineHandle) return;
            if (paused) offlineHandle.pause();
            else offlineHandle.resume();
        },
        onSpeedChange: (speed) => {
            offlineSpeed = speed;
            if (currentMode !== "offline") return;
            if (!offlineHandle) return;
            offlineHandle.setSpeed(speed);
        },
        onSeek: (tick) => {
            if (currentMode !== "offline") return;
            if (!offlineHandle) return;
            void offlineHandle.seekToTick(tick);
        },
        onRestart: () => {
            if (currentMode !== "offline") return;
            void startOffline(offlineBaseUrl, offlineSpeed);
        },
    });
    opts.mountEl.appendChild(devControls);

    const startOffline = async (baseUrl?: string, speed?: number): Promise<void> => {
        currentMode = "offline";
        if (offlineHandle) offlineHandle.stop();
        if (client) client.disconnect();
        offlineBaseUrl = baseUrl ?? offlineBaseUrl;
        if (speed && Number.isFinite(speed) && speed > 0) offlineSpeed = speed;
        store.clearDesync();
        store.setMode("offline");
        store.setConnected(true);

        try {
            offlineHandle = await startOfflineRun(store, {
                baseUrl: offlineBaseUrl,
                speed: offlineSpeed,
                overlayStore,
                viewerStore,
            });
            console.info("[webview] offline run ready:", offlineBaseUrl);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : String(err);
            console.error("[webview] offline run failed:", msg);
            store.markDesync(`Offline load failed: ${msg}`);
        }
    };

    const startLive = (liveOpts?: LiveStartOpts): void => {
        const kernelKind = liveOpts?.kernelKind ?? "sim4";
        const targetWsUrl = liveOpts?.wsUrl ?? resolveLiveWsUrl(kernelKind);
        currentMode = "live";
        if (offlineHandle) {
            offlineHandle.stop();
            offlineHandle = null;
        }
        viewerStore.setLiveKernelKind(kernelKind);
        store.clearDesync();
        store.setMode("live");
        store.setConnected(false);
        const liveClient = ensureLiveClient(targetWsUrl);

        if (import.meta.env.DEV) {
            const useMock = String(env.VITE_WEBVIEW_MOCK ?? "") === "1";
            if (useMock) {
                console.info("[webview] DEV mode: injecting mock snapshot");
                injectMockSnapshot(store);
            }

            const disableWs = String(env.VITE_WEBVIEW_DISABLE_WS ?? "") === "1";
            if (disableWs) {
                console.info("[webview] WS disabled (VITE_WEBVIEW_DISABLE_WS=1). Skipping client.connect().");
                return;
            }
        }

        console.info("[webview] connecting WS:", targetWsUrl, `kernel=${kernelKind}`);
        liveClient.connect();
    };

    const stop = (): void => {
        if (offlineHandle) {
            offlineHandle.stop();
            offlineHandle = null;
        }
        if (client) client.disconnect();
        store.setConnected(false);
    };

    const setVisible = (visible: boolean): void => {
        opts.mountEl.style.display = visible ? "block" : "none";
        if (visible) {
            requestAnimationFrame(() => {
                scene.refreshLayout({ forceAutoFit: true });
            });
        }
    };

    const setDevControlsVisible = (visible: boolean): void => {
        devControls.style.display = visible ? "block" : "none";
    };

    const setHudVisible = (visible: boolean): void => {
        hud.style.display = visible ? "block" : "none";
    };

    if (autoStart) {
        if (mode === "offline") {
            void startOffline(offlineBaseUrl, offlineSpeed);
        } else {
            startLive();
        }
    }

    return {
        startOffline,
        startLive,
        stop,
        setVisible,
        setDevControlsVisible,
        setHudVisible,
    };
}
