// src/app/boot.ts
import { WorldStore } from "../state/worldStore";
import { OverlayStore } from "../state/overlayStore";
import { ViewerStore } from "../state/viewerStore";
import { KvpClient } from "../kvp/client";
import { startOfflineRun } from "../kvp/offline";
import type { OfflineRunHandle } from "../kvp/offline";
import { PixiScene } from "../render/pixiScene";
import { mountHud, type HudProfile } from "../ui/hud";
import { mountDevControls } from "../ui/devControls";
import { mountInspectPanel } from "../ui/inspectPanel";
import { mountDialoguePanel } from "../ui/dialoguePanel";
import { mountNotebookPanel } from "../ui/notebookPanel";
import { mountResolutionPanel } from "../ui/resolutionPanel";
import { mountTimeLighting } from "../ui/timeLighting";
import { injectMockSnapshot } from "../debug/mockKernel";
import { createFrontendActionBridge } from "./actionBridge";
import { ViewerPluginRegistry } from "../viewers/core/viewerPlugin";
import { createSim4ViewerPlugin } from "../viewers/sim4/sim4Plugin";
import type {
    FrameDiffPayload as EnqueteurFrameDiffPayload,
    FullSnapshotPayload as EnqueteurFullSnapshotPayload,
    KernelHelloPayload as EnqueteurKernelHelloPayload,
} from "./live/enqueteurLiveClient";
import {
    convertLiveFrameDiff,
    convertLiveFullSnapshot,
    convertLiveKernelHello,
    convertLiveRunAnchors,
} from "./live/liveStateBridge";
import type { LiveCommandBridge } from "./live/liveCommandBridge";

export type BootMode = "live" | "offline";
export type BootShellMode = HudProfile;

export type BootOpts = {
    mountEl: HTMLElement;
    wsUrl?: string;
    offlineBaseUrl?: string;
    mode?: BootMode;
    shellMode?: BootShellMode;
    autoStart?: boolean;
};

export type ViewerHandle = {
    startOffline: (baseUrl?: string, speed?: number) => Promise<void>;
    startLive: (wsUrl?: string) => void;
    ingestLiveKernelHello?: (payload: EnqueteurKernelHelloPayload) => void;
    ingestLiveSnapshot?: (payload: EnqueteurFullSnapshotPayload) => void;
    ingestLiveFrameDiff?: (payload: EnqueteurFrameDiffPayload) => void;
    setLiveCommandBridge?: (bridge: LiveCommandBridge | null) => void;
    setShellMode?: (mode: BootShellMode) => void;
    stop: () => void;
    setVisible: (visible: boolean) => void;
    setDevControlsVisible: (visible: boolean) => void;
    setHudVisible: (visible: boolean) => void;
};

export function boot(opts: BootOpts): ViewerHandle {
    const store = new WorldStore();
    const overlayStore = new OverlayStore();
    const viewerStore = new ViewerStore();
    const env = (import.meta as any).env ?? {};
    const mode = (opts.mode ?? env.VITE_WEBVIEW_MODE ?? "offline") as BootMode;
    const autoStart = opts.autoStart ?? true;
    const defaultShellMode: BootShellMode = mode === "live" ? "playtest" : "dev";
    let offlineHandle: OfflineRunHandle | null = null;
    let offlineBaseUrl = opts.offlineBaseUrl ?? env.VITE_WEBVIEW_RUN_BASE ?? "/demo/kvp_demo_1min";
    let offlineSpeed = parseFloat(env.VITE_WEBVIEW_SPEED ?? "1");
    let currentMode: BootMode = mode;
    let shellMode: BootShellMode = opts.shellMode ?? defaultShellMode;
    let liveCommandBridge: LiveCommandBridge | null = null;
    let client: KvpClient | null = null;
    let activeLiveWsUrl: string | null = null;
    const actionBridge = createFrontendActionBridge({
        store,
        getMode: () => currentMode,
        getLiveCommandBridge: () => liveCommandBridge,
    });

    opts.mountEl.style.position = "relative";
    opts.mountEl.style.width = "100%";
    opts.mountEl.style.height = "100%";

    const scene = new PixiScene(opts.mountEl);
    const timeLighting = mountTimeLighting(opts.mountEl);

    const hud = mountHud(store, overlayStore, { profile: shellMode });
    opts.mountEl.appendChild(hud.root);

    const inspector = mountInspectPanel(store, {
        dispatchInvestigationAction: actionBridge.submitInvestigationAction,
        canDispatchInvestigationAction: actionBridge.canSubmitInvestigationAction,
    });
    opts.mountEl.appendChild(inspector.root);

    const dialoguePanel = mountDialoguePanel(store, {
        dispatchDialogueTurn: actionBridge.submitDialogueTurn,
        canDispatchDialogueTurn: actionBridge.canSubmitDialogueTurn,
    });
    opts.mountEl.appendChild(dialoguePanel.root);

    const notebookPanel = mountNotebookPanel(store, {
        dispatchMinigameSubmit: actionBridge.submitMinigameSubmit,
        canDispatchMinigameSubmit: actionBridge.canSubmitMinigameSubmit,
        allowLocalEvaluation: () => currentMode === "offline",
    });
    opts.mountEl.appendChild(notebookPanel.root);

    const resolutionPanel = mountResolutionPanel(store, {
        dispatchAttemptRecovery: actionBridge.submitAttemptRecovery,
        dispatchAttemptAccusation: actionBridge.submitAttemptAccusation,
        canDispatchResolutionAttempt: actionBridge.canSubmitResolutionAttempt,
    });
    opts.mountEl.appendChild(resolutionPanel.root);

    overlayStore.subscribe((o) => {
        scene.ingestOverlayEvents(o.eventsAtTick);
    });

    scene.onInspectSelection((sel) => {
        inspector.setSelection(sel);
        dialoguePanel.setInspectSelection(sel);
    });
    scene.onRequestFreshSnapshot(() => {
        client?.requestFreshSnapshot();
    });

    store.subscribe((s) => {
        timeLighting.update(s.world ?? null);
        scene.renderFromState(s);
    });

    let hudVisibleRequested = true;
    let devControlsVisibleRequested = true;

    const applyViewerUiVisibility = (): void => {
        const showDevControls = shellMode === "dev" && devControlsVisibleRequested;
        devControls.style.display = showDevControls ? "block" : "none";
        hud.root.style.display = hudVisibleRequested ? "block" : "none";
        inspector.root.style.display = "block";
        dialoguePanel.root.style.display = hudVisibleRequested ? "block" : "none";
        notebookPanel.root.style.display = hudVisibleRequested ? "block" : "none";
        resolutionPanel.root.style.display = hudVisibleRequested ? "block" : "none";
    };

    const pluginRegistry = new ViewerPluginRegistry();
    pluginRegistry.register(
        createSim4ViewerPlugin({
            store,
            engineName: "EnqueteurSim",
        })
    );
    pluginRegistry.register(
        createSim4ViewerPlugin({
            store,
            engineName: "Sim4",
        })
    );
    pluginRegistry.register(
        createSim4ViewerPlugin({
            store,
            engineName: "sim4",
        })
    );

    const resolveLiveWsUrl = (): string => {
        return opts.wsUrl ?? env.VITE_KVP_WS_URL_SIM4 ?? env.VITE_KVP_WS_URL ?? "ws://localhost:7777/kvp";
    };

    const ensureLiveClient = (wsUrl: string): KvpClient => {
        if (client && activeLiveWsUrl === wsUrl) return client;
        if (client) client.disconnect();
        client = new KvpClient(store, {
            url: wsUrl,
            viewerName: "enqueteur-webview-pixi",
            viewerVersion: "0.2.0",
            supportedSchemaVersions: pluginRegistry.supportedSchemaVersions(),
            defaultSubscribe: {
                stream: "LIVE",
                channels: ["WORLD", "AGENTS", "ITEMS", "EVENTS", "DEBUG"],
                diff_policy: "DIFF_ONLY",
                snapshot_policy: "ON_JOIN",
                compression: "NONE",
            },
            pluginRegistry,
        });
        const debugGlobal = globalThis as any;
        debugGlobal.__enqueteur = {
            ...(debugGlobal.__enqueteur ?? {}),
            kvpClient: client,
        };
        activeLiveWsUrl = wsUrl;
        return client;
    };

    const devControls = mountDevControls({
        store,
        viewerStore,
        onFloorChange: (floor) => scene.setFloorFilter(floor),
        onCameraModeChange: (cameraMode) => scene.setCameraMode(cameraMode),
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
    applyViewerUiVisibility();

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
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : String(err);
            store.markDesync(`Offline load failed: ${msg}`);
        }
    };

    const startLive = (wsUrl?: string): void => {
        const targetWsUrl = wsUrl ?? resolveLiveWsUrl();
        currentMode = "live";
        if (offlineHandle) {
            offlineHandle.stop();
            offlineHandle = null;
        }
        store.clearDesync();
        store.setMode("live");
        store.setConnected(false);
        const liveClient = ensureLiveClient(targetWsUrl);

        if (import.meta.env.DEV) {
            const useMock = String(env.VITE_WEBVIEW_MOCK ?? "") === "1";
            if (useMock) {
                injectMockSnapshot(store);
            }

            const disableWs = String(env.VITE_WEBVIEW_DISABLE_WS ?? "") === "1";
            if (disableWs) {
                return;
            }
        }

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
        devControlsVisibleRequested = visible;
        applyViewerUiVisibility();
    };

    const setHudVisible = (visible: boolean): void => {
        hudVisibleRequested = visible;
        applyViewerUiVisibility();
    };

    const setLiveCommandBridge = (bridge: LiveCommandBridge | null): void => {
        liveCommandBridge = bridge;
    };

    const setShellMode = (nextMode: BootShellMode): void => {
        if (shellMode === nextMode) return;
        shellMode = nextMode;
        hud.setProfile(nextMode);
        applyViewerUiVisibility();
    };

    const ingestLiveKernelHello = (payload: EnqueteurKernelHelloPayload): void => {
        store.setMode("live");
        store.setConnected(true);
        store.clearDesync();
        store.setKernelHello(convertLiveKernelHello(payload));
        store.setRunAnchors(convertLiveRunAnchors(payload));
        if (payload.render_spec && typeof payload.render_spec === "object") {
            store.setRenderSpec(payload.render_spec);
        }
    };

    const ingestLiveSnapshot = (payload: EnqueteurFullSnapshotPayload): void => {
        store.setMode("live");
        store.setConnected(true);
        store.clearDesync();
        store.applySnapshot(convertLiveFullSnapshot(payload));
    };

    const ingestLiveFrameDiff = (payload: EnqueteurFrameDiffPayload): void => {
        store.setMode("live");
        store.setConnected(true);
        store.applyDiff(convertLiveFrameDiff(payload, store.getState()));
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
        ingestLiveKernelHello,
        ingestLiveSnapshot,
        ingestLiveFrameDiff,
        setLiveCommandBridge,
        setShellMode,
        stop,
        setVisible,
        setDevControlsVisible,
        setHudVisible,
    };
}
