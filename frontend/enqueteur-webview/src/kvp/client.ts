import type {
    FrameDiffPayload,
    FullSnapshotPayload,
    KernelHello,
    WorldStore,
} from "../state/worldStore";
import type { ViewerPlugin, ViewerPluginRegistry } from "../viewers/core/viewerPlugin";

/**
 * Legacy generic KVP WebSocket client kept for sim4/offline-era debug flows.
 *
 * Canonical Enqueteur live play now goes through appFlow + EnqueteurLiveClient
 * (`src/app/live/enqueteurLiveClient.ts`) and should be treated as source of
 * truth for local human-play transport behavior.
 *
 * This client remains intentionally narrow and compatibility-oriented.
 */

/* ---------------------------------------
 * Minimal protocol types
 * ------------------------------------- */

export type KvpVersion = "0.1";

export type Channel = "WORLD" | "AGENTS" | "ITEMS" | "EVENTS" | "DEBUG";

export type DiffPolicy = "DIFF_ONLY" | "PERIODIC_SNAPSHOT" | "SNAPSHOT_ON_DESYNC";
export type SnapshotPolicy = "ON_JOIN" | "NEVER";

export type Subscribe = {
    stream: "LIVE" | "REPLAY";
    channels: Channel[];
    diff_policy: DiffPolicy;
    snapshot_policy: SnapshotPolicy;
    compression: "NONE";
};

export type MsgType =
    | "VIEWER_HELLO"
    | "KERNEL_HELLO"
    | "SUBSCRIBE"
    | "SUBSCRIBED"
    | "SIM_INPUT"
    | "FULL_SNAPSHOT"
    | "FRAME_DIFF"
    | "WARN"
    | "ERROR";

export type Envelope<TPayload = unknown> = {
    kvp_version: KvpVersion;
    msg_type: string; // keep open for forward-compat
    msg_id: string;
    sent_at_ms: number;
    payload: TPayload;
};

export type ViewerHello = {
    viewer_name: string;
    viewer_version: string;
    supported_schema_versions: string[];
    supports: {
        diff_stream: boolean;
        full_snapshot: boolean;
        replay_seek: boolean;
    };
};

/** Payloads are defined in worldStore to keep viewer state consistent. */

/* ---------------------------------------
 * Client options
 * ------------------------------------- */

export type KvpClientOpts = {
    url: string;
    viewerName: string;
    viewerVersion: string;
    supportedSchemaVersions: string[];
    defaultSubscribe: Subscribe;
    pluginRegistry: ViewerPluginRegistry;
    onPluginSelected?: (plugin: ViewerPlugin, hello: KernelHello) => void;
};

export class KvpClient {
    private ws?: WebSocket;
    private readonly store: WorldStore;
    private readonly opts: KvpClientOpts;

    private didHello = false;
    private didSubscribe = false;
    private activePlugin: ViewerPlugin | null = null;

    constructor(store: WorldStore, opts: KvpClientOpts) {
        this.store = store;
        this.opts = opts;
    }

    connect(): void {
        // Ensure we don’t leak old sockets.
        this.disconnect();

        this.didHello = false;
        this.didSubscribe = false;
        this.activePlugin = null;

        const ws = new WebSocket(this.opts.url);
        this.ws = ws;

        ws.onopen = () => {
            this.store.setConnected(true);
            this.sendViewerHello();
        };

        ws.onclose = () => {
            this.store.setConnected(false);
            this.didHello = false;
            this.didSubscribe = false;
            this.activePlugin?.deactivate();
            this.activePlugin = null;
        };

        ws.onerror = () => {
            // Don’t mark desync here; could be transient network.
            // UI can show disconnected via store.connected.
        };

        ws.onmessage = (ev) => this.onMessage(ev.data);
    }

    disconnect(): void {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            try {
                this.ws.close();
            } catch {
                // ignore
            }
        }
        this.activePlugin?.deactivate();
        this.activePlugin = null;
        this.ws = undefined;
    }

    /** Request a fresh snapshot. For v0.1, we re-send SUBSCRIBE with snapshot_policy ON_JOIN. */
    requestFreshSnapshot(): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

        // Always force ON_JOIN here, regardless of default.
        const sub: Subscribe = { ...this.opts.defaultSubscribe, snapshot_policy: "ON_JOIN" };
        this.sendEnvelope("SUBSCRIBE", sub);
    }

    /** Optional: allow switching between LIVE/REPLAY later without rebuilding client. */
    sendSubscribe(subscribe: Subscribe = this.opts.defaultSubscribe): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        this.sendEnvelope("SUBSCRIBE", subscribe);
    }

    canSendSimInput(): boolean {
        return Boolean(this.ws && this.ws.readyState === WebSocket.OPEN);
    }

    sendSimInput(payload: Record<string, unknown>): boolean {
        if (!this.canSendSimInput()) return false;
        this.sendEnvelope("SIM_INPUT", payload);
        return true;
    }

    /* ---------------------------------------
     * Outgoing messages
     * ------------------------------------- */

    private sendViewerHello(): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        if (this.didHello) return;

        const hello: ViewerHello = {
            viewer_name: this.opts.viewerName,
            viewer_version: this.opts.viewerVersion,
            supported_schema_versions: this.opts.supportedSchemaVersions,
            supports: { diff_stream: true, full_snapshot: true, replay_seek: true },
        };

        this.sendEnvelope("VIEWER_HELLO", hello);
        this.didHello = true;
    }

    private sendEnvelope<TPayload>(msg_type: MsgType, payload: TPayload): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

        const env: Envelope<TPayload> = {
            kvp_version: "0.1",
            msg_type,
            msg_id: safeUuid(),
            sent_at_ms: Date.now(),
            payload,
        };

        this.ws.send(JSON.stringify(env));
    }

    /* ---------------------------------------
     * Incoming messages
     * ------------------------------------- */

    private onMessage(raw: unknown): void {
        const text = typeof raw === "string" ? raw : raw instanceof ArrayBuffer ? new TextDecoder().decode(raw) : String(raw);

        let env: Envelope;
        try {
            env = JSON.parse(text) as Envelope;
        } catch {
            this.store.markDesync("Kernel sent invalid JSON envelope");
            return;
        }

        // Minimal envelope validation
        if (env.kvp_version !== "0.1" || typeof env.msg_type !== "string") {
            // Not necessarily desync; could be wrong server.
            this.store.markDesync("Unsupported or malformed KVP envelope");
            return;
        }

        switch (env.msg_type) {
            case "KERNEL_HELLO": {
                const hello = env.payload as KernelHello;
                const plugin = this.opts.pluginRegistry.resolve(hello.engine_name, hello.schema_version);
                if (!plugin) {
                    const mappings = this.opts.pluginRegistry.describeMappings();
                    this.store.markDesync(
                        `No viewer plugin for engine=${hello.engine_name} schema=${hello.schema_version}. Available: ${mappings || "none"}`
                    );
                    return;
                }

                if (this.activePlugin !== plugin) {
                    this.activePlugin?.deactivate();
                    this.activePlugin = plugin;
                    this.activePlugin.activate();
                }
                this.opts.onPluginSelected?.(plugin, hello);
                this.activePlugin.onKernelHello(hello);

                // Subscribe immediately after hello.
                if (!this.didSubscribe) {
                    this.sendSubscribe(this.opts.defaultSubscribe);
                    this.didSubscribe = true;
                }
                break;
            }

            case "SUBSCRIBED": {
                // Optional: store stream_id + effective policies if you expose in UI later.
                break;
            }

            case "FULL_SNAPSHOT": {
                const snap = env.payload as FullSnapshotPayload;
                if (!this.activePlugin) {
                    this.store.markDesync("FULL_SNAPSHOT received before KERNEL_HELLO/plugin selection");
                    return;
                }
                try {
                    this.activePlugin.onFullSnapshot(snap);
                } catch (err) {
                    const msg = err instanceof Error ? err.message : String(err);
                    this.store.markDesync(`Plugin snapshot error: ${msg}`);
                }
                break;
            }

            case "FRAME_DIFF": {
                const diff = env.payload as FrameDiffPayload;
                if (!this.activePlugin) {
                    this.store.markDesync("FRAME_DIFF received before KERNEL_HELLO/plugin selection");
                    return;
                }
                try {
                    this.activePlugin.onFrameDiff(diff);
                } catch (err) {
                    const msg = err instanceof Error ? err.message : String(err);
                    this.store.markDesync(`Plugin diff error: ${msg}`);
                }
                break;
            }

            case "WARN": {
                // Optional: route to UI notifications (non-fatal)
                break;
            }

            case "ERROR": {
                // Optional: surface and possibly disconnect
                break;
            }

            default: {
                this.store.markDesync(`Unknown msg_type: ${env.msg_type}`);
                break;
            }
        }
    }
}

/* ---------------------------------------
 * Utils
 * ------------------------------------- */

function safeUuid(): string {
    // Browser-safe UUID without requiring polyfills.
    const c = globalThis.crypto as Crypto | undefined;
    if (c?.randomUUID) return c.randomUUID();

    // Fallback: not a true UUID, but stable enough for message IDs.
    return `msg_${Date.now().toString(16)}_${Math.random().toString(16).slice(2)}`;
}
