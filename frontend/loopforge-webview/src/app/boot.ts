// src/app/boot.ts
import { WorldStore } from "../state/worldStore";
import { KvpClient } from "../kvp/client";
import { PixiScene } from "../render/pixiScene";
import { mountHud } from "../ui/hud";
import { injectMockSnapshot } from "../debug/mockKernel";

/**
 * Boot the Loopforge Web Viewer (WEBVIEW-0001).
 * - Protocol-first (KVP-0001)
 * - No simulation logic
 * - Web viewer is a client: snapshot + diff → render
 */
export function boot(opts: { mountEl: HTMLElement; wsUrl: string }): void {
    const store = new WorldStore();

    // Mount container should be positioning context for HUD overlays.
    opts.mountEl.style.position = "relative";
    opts.mountEl.style.width = "100%";
    opts.mountEl.style.height = "100%";

    // Renderer (PixiJS)
    const scene = new PixiScene(opts.mountEl);

    // HUD (DOM overlay)
    const hud = mountHud(store);
    opts.mountEl.appendChild(hud);

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
        // --- DEBUG: prove we have data, and that render is called -------------
        console.debug("[webview] state", {
            tick: s.tick,
            rooms: s.rooms.size,
            agents: s.agents.size,
            narrative: s.narrative.size,
            desynced: s.desynced,
            reason: s.desyncReason ?? null,
            stepHash: s.stepHash ?? null,
        });

        scene.renderFromState(s);
    });

    // KVP client
    const client = new KvpClient(store, {
        url: opts.wsUrl,
        viewerName: "loopforge-webview-pixi",
        viewerVersion: "0.1.0",
        supportedSchemaVersions: ["2"],
        defaultSubscribe: {
            stream: "LIVE",
            channels: ["WORLD", "AGENTS", "EVENTS", "DEBUG", "NARRATIVE"],
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
        console.info("[webview] DEV mode: injecting mock snapshot");
        injectMockSnapshot(store);

        // --- DEBUG: optionally run webview without WS to avoid overwriting mock
        // Set VITE_WEBVIEW_DISABLE_WS=1 to keep the mock state on screen.
        const disableWs = String((import.meta as any).env?.VITE_WEBVIEW_DISABLE_WS ?? "") === "1";
        if (disableWs) {
            console.info("[webview] WS disabled (VITE_WEBVIEW_DISABLE_WS=1). Skipping client.connect().");
            return;
        }
    }

    // Connect!
    console.info("[webview] connecting WS:", opts.wsUrl);
    client.connect();
}
