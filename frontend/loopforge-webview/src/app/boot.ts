// src/app/boot.ts
import { WorldStore } from "../state/worldStore";
import { KvpClient } from "../kvp/client";
import { PixiScene } from "../render/pixiScene";
import { mountHud } from "../ui/hud";

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

    // Render on state changes (simple + correct; later you can batch)
    store.subscribe((s) => scene.renderFromState(s));

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
    scene.onRequestFreshSnapshot(() => client.requestFreshSnapshot());

    // Connect!
    client.connect();
}
