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
import { ViewerPluginRegistry } from "../viewers/core/viewerPlugin";
import { createSim4ViewerPlugin } from "../viewers/sim4/sim4Plugin";
import { createSimSimViewerPlugin } from "../viewers/sim_sim/simSimPlugin";
import { SimSimScene } from "../viewers/sim_sim/simSimScene";
import { SIM_SIM_SCHEMA_VERSION, SimSimStore } from "../viewers/sim_sim/simSimStore";

/**
 * Boot the Loopforge Web Viewer (WEBVIEW-0001).
 * - Protocol-first (KVP-0001 transport)
 * - Engine/plugin-routed rendering pipelines
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
    const simSimStore = new SimSimStore();

    // Mount container should be positioning context for HUD overlays.
    opts.mountEl.style.position = "relative";
    opts.mountEl.style.width = "100%";
    opts.mountEl.style.height = "100%";

    // Renderers
    const sim4Scene = new PixiScene(opts.mountEl);
    let simSimScene: SimSimScene | null = null;
    sim4Scene.setVisible(true);

    const timeLighting = mountTimeLighting(opts.mountEl);

    // HUD (DOM overlay)
    const hud = mountHud(store, overlayStore);
    opts.mountEl.appendChild(hud);

    // Inspector (DOM overlay)
    const inspector = mountInspectPanel(store);
    opts.mountEl.appendChild(inspector.root);

    overlayStore.subscribe((o) => {
        sim4Scene.ingestOverlayEvents(o.eventsAtTick);
    });

    sim4Scene.onInspectSelection((sel) => inspector.setSelection(sel));
    sim4Scene.onRequestFreshSnapshot(() => {
        console.warn("[webview] desync banner: requesting fresh snapshot");
        client?.requestFreshSnapshot();
    });

    // --- DEBUG: prove canvases exist + have size (Pixi v8 async init) ----------
    const debugCanvasProbe = () => {
        const canvases = Array.from(opts.mountEl.querySelectorAll("canvas"));
        const rects = canvases.map((canvas) => {
            const rect = canvas.getBoundingClientRect();
            return { w: Math.round(rect.width), h: Math.round(rect.height) };
        });
        console.debug("[webview] canvas probe", { count: canvases.length, rects });
    };
    debugCanvasProbe();
    setTimeout(debugCanvasProbe, 0);
    setTimeout(debugCanvasProbe, 250);

    // Render on state changes.
    store.subscribe((s) => {
        console.debug("[webview] sim4 state", {
            tick: s.tick,
            rooms: s.rooms.size,
            agents: s.agents.size,
            items: s.items.size,
            desynced: s.desynced,
            reason: s.desyncReason ?? null,
            stepHash: s.stepHash ?? null,
        });
        timeLighting.update(s.world ?? null);
        sim4Scene.renderFromState(s);
    });
    simSimStore.subscribe((s) => {
        console.debug("[webview] sim_sim state", {
            tick: s.tick,
            rooms: s.rooms.size,
            supervisors: s.supervisors.size,
            cash: s.inventory?.cash ?? null,
            desynced: s.desynced,
            reason: s.desyncReason ?? null,
            stepHash: s.stepHash ?? null,
            lastMsgType: s.lastMsgType ?? null,
            lastAppliedDiffCount: s.lastAppliedDiffCount,
        });
        simSimScene?.renderFromState(s);
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

    let activeRenderer: LiveKernelKind = "sim4";
    let hudVisibleRequested = true;
    let devControlsVisibleRequested = true;

    const applyViewerUiVisibility = (): void => {
        const sim4Active = activeRenderer === "sim4";
        devControls.style.display = sim4Active && devControlsVisibleRequested ? "block" : "none";
        hud.style.display = sim4Active && hudVisibleRequested ? "block" : "none";
        inspector.root.style.display = sim4Active ? "block" : "none";
        if (!sim4Active) timeLighting.update(null);
    };

    const ensureSimSimScene = (): SimSimScene => {
        if (simSimScene) return simSimScene;
        simSimScene = new SimSimScene(opts.mountEl, {
            onSubmitPromptChoice: ({ tickTarget, promptId, choice }) => {
                if (!client) {
                    console.warn("[webview] sim_sim prompt response ignored: live client not connected");
                    return;
                }
                client.sendSimInput({
                    schema: SIM_SIM_SCHEMA_VERSION,
                    tick_target: tickTarget,
                    payload: {
                        prompt_responses: {
                            [promptId]: choice,
                        },
                    },
                });
            },
        });
        simSimScene.setVisible(false);
        return simSimScene;
    };

    const activateSim4Viewer = (): void => {
        activeRenderer = "sim4";
        sim4Scene.setVisible(true);
        simSimScene?.setVisible(false);
        applyViewerUiVisibility();
    };

    const activateSimSimViewer = (): void => {
        activeRenderer = "sim_sim";
        const simSim = ensureSimSimScene();
        sim4Scene.setVisible(false);
        simSim.setVisible(true);
        applyViewerUiVisibility();
    };

    const pluginRegistry = new ViewerPluginRegistry();
    pluginRegistry.register(
        createSim4ViewerPlugin({
            store,
            onActivate: activateSim4Viewer,
        })
    );
    pluginRegistry.register(
        createSim4ViewerPlugin({
            store,
            engineName: "sim4",
            onActivate: activateSim4Viewer,
        })
    );
    pluginRegistry.register(
        createSimSimViewerPlugin({
            store: simSimStore,
            onActivate: activateSimSimViewer,
        })
    );

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
            supportedSchemaVersions: pluginRegistry.supportedSchemaVersions(),
            defaultSubscribe: {
                stream: "LIVE",
                channels: ["WORLD", "AGENTS", "ITEMS", "EVENTS", "DEBUG"],
                diff_policy: "DIFF_ONLY",
                snapshot_policy: "ON_JOIN",
                compression: "NONE",
            },
            pluginRegistry,
            onPluginSelected: (plugin, hello) => {
                console.info(
                    "[webview] viewer plugin selected",
                    plugin.id,
                    `engine=${hello.engine_name}`,
                    `schema=${hello.schema_version}`
                );
                viewerStore.setLiveKernelKind(hello.engine_name === "sim_sim" ? "sim_sim" : "sim4");
            },
        });
        const debugGlobal = globalThis as any;
        debugGlobal.__loopforge = {
            ...(debugGlobal.__loopforge ?? {}),
            kvpClient: client,
        };
        activeLiveWsUrl = wsUrl;
        return client;
    };

    const devControls = mountDevControls({
        store,
        viewerStore,
        onFloorChange: (floor) => sim4Scene.setFloorFilter(floor),
        onCameraModeChange: (cameraMode) => sim4Scene.setCameraMode(cameraMode),
        onRotate: (delta) => sim4Scene.rotateView(delta),
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
    applyViewerUiVisibility();

    const startOffline = async (baseUrl?: string, speed?: number): Promise<void> => {
        currentMode = "offline";
        if (offlineHandle) offlineHandle.stop();
        if (client) client.disconnect();
        activateSim4Viewer();
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
        if (kernelKind === "sim_sim") activateSimSimViewer();
        else activateSim4Viewer();
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
                sim4Scene.refreshLayout({ forceAutoFit: true });
                simSimScene?.refreshLayout({ forceAutoFit: true });
            });
        }
    };

    const setDevControlsVisible = (visible: boolean): void => {
        devControlsVisibleRequested = visible;
        applyViewerUiVisibility();
    };

    const setHudVisible = (visible: boolean): void => {
        hudVisibleRequested = visible;
        applyViewerUiVisibility();
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
