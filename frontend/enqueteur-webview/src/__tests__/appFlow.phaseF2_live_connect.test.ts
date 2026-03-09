import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mountAppFlow, type AppFlowOpts } from "../app/appFlow";
import type {
    CaseLaunchClient,
    CaseLaunchMetadata,
} from "../app/api/caseLaunchClient";
import type {
    EnqueteurInboundEnvelopeByType,
    EnqueteurInboundMsgType,
    EnqueteurLiveClientLike,
    EnqueteurLiveProtocolError,
} from "../app/live/enqueteurLiveClient";

function makeMountEl(): HTMLElement {
    const mountEl = document.createElement("div");
    document.body.appendChild(mountEl);
    return mountEl;
}

async function flushAsyncWork(): Promise<void> {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
}

function makeLaunchMetadata(): CaseLaunchMetadata {
    return {
        runId: "run-123",
        worldId: "world-123",
        caseId: "MBAM_01",
        seed: "A",
        resolvedSeedId: "A",
        difficultyProfile: "D0",
        mode: "playtest",
        engineName: "enqueteur",
        schemaVersion: "enqueteur_mbam_1",
        wsUrl: "ws://localhost:7777/live?run_id=run-123",
        startedAt: "2026-03-09T10:00:00Z",
    };
}

function clickFirstCaseCard(): void {
    const card = document.querySelector<HTMLButtonElement>(".flow-case-card");
    if (!card) throw new Error("case card not found");
    card.click();
}

class ScriptedLiveClient implements EnqueteurLiveClientLike {
    readonly connect = vi.fn(() => {});
    readonly disconnect = vi.fn((_code?: number, _reason?: string) => {});
    readonly sendSubscribe = vi.fn(() => true);

    private readonly openHandlers = new Set<() => void>();
    private readonly closeHandlers = new Set<(event: CloseEvent) => void>();
    private readonly transportErrorHandlers = new Set<(event: Event) => void>();
    private readonly protocolErrorHandlers = new Set<(error: EnqueteurLiveProtocolError) => void>();
    private readonly messageHandlers = new Map<
        EnqueteurInboundMsgType,
        Set<(envelope: EnqueteurInboundEnvelopeByType[EnqueteurInboundMsgType]) => void>
    >();

    onOpen(handler: () => void): () => void {
        this.openHandlers.add(handler);
        return () => this.openHandlers.delete(handler);
    }

    onClose(handler: (event: CloseEvent) => void): () => void {
        this.closeHandlers.add(handler);
        return () => this.closeHandlers.delete(handler);
    }

    onTransportError(handler: (event: Event) => void): () => void {
        this.transportErrorHandlers.add(handler);
        return () => this.transportErrorHandlers.delete(handler);
    }

    onProtocolError(handler: (error: EnqueteurLiveProtocolError) => void): () => void {
        this.protocolErrorHandlers.add(handler);
        return () => this.protocolErrorHandlers.delete(handler);
    }

    onMessage<T extends EnqueteurInboundMsgType>(
        msgType: T,
        handler: (envelope: EnqueteurInboundEnvelopeByType[T]) => void
    ): () => void {
        const bucket = this.messageHandlers.get(msgType)
            ?? new Set<(envelope: EnqueteurInboundEnvelopeByType[EnqueteurInboundMsgType]) => void>();
        bucket.add(handler as (envelope: EnqueteurInboundEnvelopeByType[EnqueteurInboundMsgType]) => void);
        this.messageHandlers.set(msgType, bucket);
        return () => {
            bucket.delete(handler as (envelope: EnqueteurInboundEnvelopeByType[EnqueteurInboundMsgType]) => void);
        };
    }

    emitOpen(): void {
        for (const handler of this.openHandlers) handler();
    }

    emitClose(code = 1006, reason = "abnormal close"): void {
        const event = { code, reason } as CloseEvent;
        for (const handler of this.closeHandlers) handler(event);
    }

    emitTransportError(): void {
        for (const handler of this.transportErrorHandlers) handler(new Event("error"));
    }

    emitProtocolError(error: EnqueteurLiveProtocolError): void {
        for (const handler of this.protocolErrorHandlers) handler(error);
    }

    emitMessage<T extends EnqueteurInboundMsgType>(
        msgType: T,
        payload: EnqueteurInboundEnvelopeByType[T]["payload"]
    ): void {
        const handlers = this.messageHandlers.get(msgType);
        if (!handlers) return;
        const envelope = {
            kvp_version: "0.1",
            msg_type: msgType,
            msg_id: "msg-123",
            sent_at_ms: 123,
            payload,
        } as EnqueteurInboundEnvelopeByType[T];
        for (const handler of handlers) {
            handler(envelope as EnqueteurInboundEnvelopeByType[EnqueteurInboundMsgType]);
        }
    }
}

beforeEach(() => {
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb: FrameRequestCallback) => {
        cb(performance.now());
        return 1;
    });
});

afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
});

describe("Phase F2 live connect app flow", () => {
    it("uses launch metadata to start live connect and advances explicit connecting phases", async () => {
        let resolveStartCase: (value: CaseLaunchMetadata) => void = () => {};
        const startCase = vi.fn(
            () =>
                new Promise<CaseLaunchMetadata>((resolve) => {
                    resolveStartCase = resolve;
                })
        );
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const scriptedLiveClient = new ScriptedLiveClient();
        const createLiveClient = vi.fn(() => scriptedLiveClient);

        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();
        resolveStartCase(makeLaunchMetadata());
        await flushAsyncWork();

        expect(createLiveClient).toHaveBeenCalledWith(expect.objectContaining({
            runId: "run-123",
            worldId: "world-123",
            wsUrl: "ws://localhost:7777/live?run_id=run-123",
            engineName: "enqueteur",
            schemaVersion: "enqueteur_mbam_1",
        }));
        expect(scriptedLiveClient.connect).toHaveBeenCalledTimes(1);
        expect(flow.getState()).toEqual({
            kind: "CONNECTING",
            caseId: "MBAM_01",
            phase: "SESSION_STARTUP",
        });

        scriptedLiveClient.emitOpen();
        expect(flow.getState()).toEqual({
            kind: "CONNECTING",
            caseId: "MBAM_01",
            phase: "HANDSHAKING",
        });

        scriptedLiveClient.emitMessage("KERNEL_HELLO", {
            engine_name: "enqueteur",
            engine_version: "0.1.0",
            schema_version: "enqueteur_mbam_1",
            world_id: "world-123",
            run_id: "run-123",
            seed: "A",
            tick_rate_hz: 30,
            time_origin_ms: 0,
            render_spec: {},
        });
        expect(scriptedLiveClient.sendSubscribe).toHaveBeenCalledTimes(1);

        scriptedLiveClient.emitMessage("SUBSCRIBED", {
            stream_id: "stream-123",
            effective_stream: "LIVE",
            effective_channels: ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
            effective_diff_policy: "DIFF_ONLY",
            effective_snapshot_policy: "ON_JOIN",
            effective_compression: "NONE",
        });
        expect(flow.getState()).toEqual({
            kind: "CONNECTING",
            caseId: "MBAM_01",
            phase: "WAITING_FOR_BASELINE",
        });

        scriptedLiveClient.emitMessage("FULL_SNAPSHOT", {
            schema_version: "enqueteur_mbam_1",
            tick: 0,
            step_hash: "hash-0",
            state: {},
        });
        expect(flow.getState()).toEqual({
            kind: "CONNECTING",
            caseId: "MBAM_01",
            phase: "SESSION_READY",
        });

        flow.destroy();
    });

    it("routes protocol incompatibility failures into startup incompatibility", async () => {
        const startCase = vi.fn(async () => makeLaunchMetadata());
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const scriptedLiveClient = new ScriptedLiveClient();
        const createLiveClient = vi.fn(() => scriptedLiveClient);
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();
        await flushAsyncWork();

        scriptedLiveClient.emitProtocolError({
            name: "EnqueteurLiveProtocolError",
            message: "Expected KERNEL_HELLO.engine_name=enqueteur, got wrong-engine.",
            code: "UNEXPECTED_KERNEL_IDENTITY",
        } as EnqueteurLiveProtocolError);

        expect(flow.getState()).toEqual({
            kind: "ERROR",
            code: "STARTUP_INCOMPATIBILITY",
            message: "Live protocol error (UNEXPECTED_KERNEL_IDENTITY): Expected KERNEL_HELLO.engine_name=enqueteur, got wrong-engine.",
            recoverTo: "MAIN_MENU",
        });

        flow.destroy();
    });
});
