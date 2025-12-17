// src/kvp/client.ts
import type { WorldStore } from "../state/worldStore";

/**
 * KVP-0001 WebSocket client (WEBVIEW-0001).
 * - Protocol-first: ViewerHello → KernelHello → Subscribe → Snapshot/Diff stream
 * - No simulation logic.
 * - Forward-compatible: unknown msg types are ignored.
 *
 * NOTE: This file includes minimal type definitions to compile immediately.
 * Later, move these into src/kvp/types.ts + schema-generated types.
 */

/* ---------------------------------------
 * Minimal protocol types
 * ------------------------------------- */

export type KvpVersion = "0.1";

export type Channel = "WORLD" | "AGENTS" | "ITEMS" | "EVENTS" | "NARRATIVE" | "DEBUG";

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

export type KernelHello = {
    engine_name: string;
    engine_version: string;
    schema_version: string;
    world_id: string;
    run_id: string;
    seed: number;
    tick_rate_hz: number;
    time_origin_ms?: number;
};

/** Placeholder shapes so the client can route payloads.
 * Real schemas live in KVP spec + your generated types.
 */
export type FullSnapshot = any;
export type FrameDiff = any;

/* ---------------------------------------
 * Client options
 * ------------------------------------- */

export type KvpClientOpts = {
    url: string;
    viewerName: string;
    viewerVersion: string;
    supportedSchemaVersions: string[];
    defaultSubscribe: Subscribe;
};

export class KvpClient {
    private ws?: WebSocket;
    private readonly store: WorldStore;
    private readonly opts: KvpClientOpts;

    private didHello = false;
    private didSubscribe = false;

    constructor(store: WorldStore, opts: KvpClientOpts) {
        this.store = store;
        this.opts = opts;
    }

    connect(): void {
        // Ensure we don’t leak old sockets.
        this.disconnect();

        this.didHello = false;
        this.didSubscribe = false;

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
                this.store.setKernelHello(hello);

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
                const snap = env.payload as FullSnapshot;
                this.store.applySnapshot(snap);
                break;
            }

            case "FRAME_DIFF": {
                const diff = env.payload as FrameDiff;
                this.store.applyDiff(diff);
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
                // Forward-compat: ignore unknown message types.
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
