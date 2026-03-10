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
import type { ViewerHandle } from "../app/boot";

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

function makeFakeViewer() {
    return {
        startOffline: vi.fn(async () => {}),
        startLive: vi.fn(() => {}),
        ingestLiveKernelHello: vi.fn((_payload: unknown) => {}),
        ingestLiveSnapshot: vi.fn((_payload: unknown) => {}),
        ingestLiveFrameDiff: vi.fn((_payload: unknown) => {}),
        setLiveCommandBridge: vi.fn((_bridge: unknown) => {}),
        stop: vi.fn(() => {}),
        setVisible: vi.fn((_visible: boolean) => {}),
        setDevControlsVisible: vi.fn((_visible: boolean) => {}),
        setHudVisible: vi.fn((_visible: boolean) => {}),
    };
}

class ScriptedLiveClient implements EnqueteurLiveClientLike {
    readonly connect = vi.fn(() => {});
    readonly disconnect = vi.fn((_code?: number, _reason?: string) => {});
    readonly sendSubscribe = vi.fn(() => true);
    readonly sendInputCommand = vi.fn((payload: { client_cmd_id: string }) => Boolean(payload.client_cmd_id));

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
        const fakeViewer = makeFakeViewer();
        const createLiveViewer: NonNullable<AppFlowOpts["createLiveViewer"]> = vi.fn(
            async () => fakeViewer
        );

        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
            createLiveViewer,
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
        expect(scriptedLiveClient.sendSubscribe).toHaveBeenCalledWith({
            stream: "LIVE",
            channels: ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
            diff_policy: "DIFF_ONLY",
            snapshot_policy: "ON_JOIN",
            compression: "NONE",
        });

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
            state: { world: {} },
        });
        await flushAsyncWork();
        expect(flow.getState()).toEqual({
            kind: "LIVE_GAME",
            caseId: "MBAM_01",
        });
        expect(createLiveViewer).toHaveBeenCalledTimes(1);
        expect(fakeViewer.ingestLiveKernelHello).toHaveBeenCalledTimes(1);
        expect(fakeViewer.ingestLiveSnapshot).toHaveBeenCalledTimes(1);

        scriptedLiveClient.emitMessage("FRAME_DIFF", {
            schema_version: "enqueteur_mbam_1",
            from_tick: 0,
            to_tick: 1,
            prev_step_hash: "hash-0",
            step_hash: "hash-1",
            ops: [],
        });
        expect(fakeViewer.ingestLiveFrameDiff).toHaveBeenCalledTimes(1);

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

    it("treats subscribe acknowledgement mismatches as startup incompatibility", async () => {
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

        scriptedLiveClient.emitOpen();
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
        scriptedLiveClient.emitMessage("SUBSCRIBED", {
            stream_id: "stream-123",
            effective_stream: "LIVE",
            effective_channels: ["WORLD", "DEBUG"],
            effective_diff_policy: "DIFF_ONLY",
            effective_snapshot_policy: "ON_JOIN",
            effective_compression: "NONE",
        });

        expect(flow.getState()).toEqual({
            kind: "ERROR",
            code: "STARTUP_INCOMPATIBILITY",
            message: "SUBSCRIBED includes unexpected channels: DEBUG.",
            recoverTo: "MAIN_MENU",
        });

        flow.destroy();
    });

    it("rejects FRAME_DIFF before baseline as a startup protocol failure", async () => {
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

        scriptedLiveClient.emitOpen();
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
        scriptedLiveClient.emitMessage("SUBSCRIBED", {
            stream_id: "stream-123",
            effective_stream: "LIVE",
            effective_channels: ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
            effective_diff_policy: "DIFF_ONLY",
            effective_snapshot_policy: "ON_JOIN",
            effective_compression: "NONE",
        });
        scriptedLiveClient.emitMessage("FRAME_DIFF", {
            schema_version: "enqueteur_mbam_1",
            from_tick: 0,
            to_tick: 1,
            prev_step_hash: "hash-0",
            step_hash: "hash-1",
            ops: [],
        });

        expect(flow.getState()).toEqual({
            kind: "ERROR",
            code: "STARTUP_INCOMPATIBILITY",
            message: "FRAME_DIFF arrived before baseline handoff completed.",
            recoverTo: "MAIN_MENU",
        });

        flow.destroy();
    });

    it("buffers FRAME_DIFF until LIVE_GAME viewer mount is ready", async () => {
        const startCase = vi.fn(async () => makeLaunchMetadata());
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const scriptedLiveClient = new ScriptedLiveClient();
        const createLiveClient = vi.fn(() => scriptedLiveClient);
        const fakeViewer = makeFakeViewer();
        let resolveViewer: (value: ViewerHandle) => void = () => {};
        const createLiveViewer: NonNullable<AppFlowOpts["createLiveViewer"]> = vi.fn(
            () =>
                new Promise<ViewerHandle>((resolve) => {
                    resolveViewer = resolve;
                })
        );
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
            createLiveViewer,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();
        await flushAsyncWork();

        scriptedLiveClient.emitOpen();
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
        scriptedLiveClient.emitMessage("SUBSCRIBED", {
            stream_id: "stream-123",
            effective_stream: "LIVE",
            effective_channels: ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
            effective_diff_policy: "DIFF_ONLY",
            effective_snapshot_policy: "ON_JOIN",
            effective_compression: "NONE",
        });
        scriptedLiveClient.emitMessage("FULL_SNAPSHOT", {
            schema_version: "enqueteur_mbam_1",
            tick: 0,
            step_hash: "hash-0",
            state: { world: {} },
        });
        scriptedLiveClient.emitMessage("FRAME_DIFF", {
            schema_version: "enqueteur_mbam_1",
            from_tick: 0,
            to_tick: 1,
            prev_step_hash: "hash-0",
            step_hash: "hash-1",
            ops: [],
        });

        expect(fakeViewer.ingestLiveSnapshot).toHaveBeenCalledTimes(0);
        expect(fakeViewer.ingestLiveFrameDiff).toHaveBeenCalledTimes(0);

        resolveViewer(fakeViewer);
        await flushAsyncWork();

        expect(fakeViewer.ingestLiveSnapshot).toHaveBeenCalledTimes(1);
        expect(fakeViewer.ingestLiveFrameDiff).toHaveBeenCalledTimes(1);
        expect(flow.getState()).toEqual({
            kind: "LIVE_GAME",
            caseId: "MBAM_01",
        });

        flow.destroy();
    });

    it("correlates live INPUT_COMMAND acknowledgements by client_cmd_id", async () => {
        const startCase = vi.fn(async () => makeLaunchMetadata());
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const scriptedLiveClient = new ScriptedLiveClient();
        const createLiveClient = vi.fn(() => scriptedLiveClient);
        const fakeViewer = makeFakeViewer();
        const createLiveViewer: NonNullable<AppFlowOpts["createLiveViewer"]> = vi.fn(
            async () => fakeViewer
        );
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
            createLiveViewer,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();
        await flushAsyncWork();

        scriptedLiveClient.emitOpen();
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
        scriptedLiveClient.emitMessage("SUBSCRIBED", {
            stream_id: "stream-123",
            effective_stream: "LIVE",
            effective_channels: ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
            effective_diff_policy: "DIFF_ONLY",
            effective_snapshot_policy: "ON_JOIN",
            effective_compression: "NONE",
        });
        scriptedLiveClient.emitMessage("FULL_SNAPSHOT", {
            schema_version: "enqueteur_mbam_1",
            tick: 0,
            step_hash: "hash-0",
            state: { world: {} },
        });
        await flushAsyncWork();

        const bridgeCall = fakeViewer.setLiveCommandBridge.mock.calls.at(-1);
        const liveBridge = bridgeCall?.[0] as {
            sendInputCommand: (
                cmd: { type: "INVESTIGATE_OBJECT"; payload: Record<string, unknown> },
                opts?: { tickTarget?: number }
            ) => Promise<{ accepted: boolean; clientCmdId: string; reasonCode?: string; message?: string }>;
        };
        expect(liveBridge).toBeTruthy();

        const rejectedPromise = liveBridge.sendInputCommand(
            {
                type: "INVESTIGATE_OBJECT",
                payload: { object_id: "O1_DISPLAY_CASE", action_id: "inspect" },
            },
            { tickTarget: 1 }
        );
        expect(scriptedLiveClient.sendInputCommand).toHaveBeenCalledTimes(1);

        const firstCall = scriptedLiveClient.sendInputCommand.mock.calls[0];
        expect(firstCall).toBeTruthy();
        const firstCommandPayload = firstCall![0];
        scriptedLiveClient.emitMessage("COMMAND_REJECTED", {
            client_cmd_id: firstCommandPayload.client_cmd_id,
            reason_code: "OBJECT_ACTION_UNAVAILABLE",
            message: "Object action unavailable.",
        });

        await expect(rejectedPromise).resolves.toEqual({
            accepted: false,
            clientCmdId: firstCommandPayload.client_cmd_id,
            reasonCode: "OBJECT_ACTION_UNAVAILABLE",
            message: "Object action unavailable.",
        });

        const acceptedPromise = liveBridge.sendInputCommand(
            {
                type: "INVESTIGATE_OBJECT",
                payload: { object_id: "O1_DISPLAY_CASE", action_id: "inspect" },
            },
            { tickTarget: 2 }
        );
        expect(scriptedLiveClient.sendInputCommand).toHaveBeenCalledTimes(2);
        const secondCall = scriptedLiveClient.sendInputCommand.mock.calls[1];
        expect(secondCall).toBeTruthy();
        const secondCommandPayload = secondCall![0];
        scriptedLiveClient.emitMessage("COMMAND_ACCEPTED", {
            client_cmd_id: secondCommandPayload.client_cmd_id,
        });

        await expect(acceptedPromise).resolves.toEqual({
            accepted: true,
            clientCmdId: secondCommandPayload.client_cmd_id,
            reasonCode: undefined,
            message: undefined,
        });

        flow.destroy();
    });

    it("routes LIVE_GAME socket disconnects to recoverable connection failure and supports retry", async () => {
        const startCase = vi.fn(async () => makeLaunchMetadata());
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const scriptedLiveClient = new ScriptedLiveClient();
        const createLiveClient = vi.fn(() => scriptedLiveClient);
        const fakeViewer = makeFakeViewer();
        const createLiveViewer: NonNullable<AppFlowOpts["createLiveViewer"]> = vi.fn(
            async () => fakeViewer
        );
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
            createLiveViewer,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();
        await flushAsyncWork();

        scriptedLiveClient.emitOpen();
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
        scriptedLiveClient.emitMessage("SUBSCRIBED", {
            stream_id: "stream-123",
            effective_stream: "LIVE",
            effective_channels: ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
            effective_diff_policy: "DIFF_ONLY",
            effective_snapshot_policy: "ON_JOIN",
            effective_compression: "NONE",
        });
        scriptedLiveClient.emitMessage("FULL_SNAPSHOT", {
            schema_version: "enqueteur_mbam_1",
            tick: 0,
            step_hash: "hash-0",
            state: { world: {} },
        });
        await flushAsyncWork();

        scriptedLiveClient.emitClose(1006, "network_lost");
        expect(flow.getState()).toEqual({
            kind: "ERROR",
            code: "CONNECTION_FAILURE",
            message: "Live session disconnected (code 1006, reason: network_lost).",
            recoverTo: "CASE_SELECT",
        });

        const retryButton = Array.from(document.querySelectorAll<HTMLButtonElement>(".flow-action-btn"))
            .find((btn) => btn.textContent === "Retry Connection");
        expect(retryButton).toBeTruthy();
        retryButton?.click();

        expect(createLiveClient).toHaveBeenCalledTimes(2);
        expect(scriptedLiveClient.connect).toHaveBeenCalledTimes(2);
        expect(flow.getState()).toEqual({
            kind: "CONNECTING",
            caseId: "MBAM_01",
            phase: "SESSION_STARTUP",
        });

        flow.destroy();
    });

    it("surfaces WARN during CONNECTING and keeps non-fatal runtime ERROR out of fatal flow", async () => {
        const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
        const startCase = vi.fn(async () => makeLaunchMetadata());
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const scriptedLiveClient = new ScriptedLiveClient();
        const createLiveClient = vi.fn(() => scriptedLiveClient);
        const fakeViewer = makeFakeViewer();
        const createLiveViewer: NonNullable<AppFlowOpts["createLiveViewer"]> = vi.fn(
            async () => fakeViewer
        );
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
            createLiveViewer,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();
        await flushAsyncWork();

        scriptedLiveClient.emitMessage("WARN", {
            code: "DEGRADED_MODE",
            message: "backend warming caches",
        });
        expect(document.body.textContent).toContain("Live warning (DEGRADED_MODE): backend warming caches");

        scriptedLiveClient.emitOpen();
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
        scriptedLiveClient.emitMessage("SUBSCRIBED", {
            stream_id: "stream-123",
            effective_stream: "LIVE",
            effective_channels: ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
            effective_diff_policy: "DIFF_ONLY",
            effective_snapshot_policy: "ON_JOIN",
            effective_compression: "NONE",
        });
        scriptedLiveClient.emitMessage("FULL_SNAPSHOT", {
            schema_version: "enqueteur_mbam_1",
            tick: 0,
            step_hash: "hash-0",
            state: { world: {} },
        });
        await flushAsyncWork();

        scriptedLiveClient.emitMessage("ERROR", {
            code: "INTERNAL_RUNTIME_ERROR",
            message: "temporary degradation",
            fatal: false,
        });

        expect(flow.getState()).toEqual({
            kind: "LIVE_GAME",
            caseId: "MBAM_01",
        });
        expect(warnSpy).toHaveBeenCalledWith("Live warning (INTERNAL_RUNTIME_ERROR): temporary degradation");

        flow.destroy();
    });

    it("routes fatal backend ERROR during LIVE_GAME into connection failure", async () => {
        const startCase = vi.fn(async () => makeLaunchMetadata());
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const scriptedLiveClient = new ScriptedLiveClient();
        const createLiveClient = vi.fn(() => scriptedLiveClient);
        const fakeViewer = makeFakeViewer();
        const createLiveViewer: NonNullable<AppFlowOpts["createLiveViewer"]> = vi.fn(
            async () => fakeViewer
        );
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
            createLiveViewer,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();
        await flushAsyncWork();

        scriptedLiveClient.emitOpen();
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
        scriptedLiveClient.emitMessage("SUBSCRIBED", {
            stream_id: "stream-123",
            effective_stream: "LIVE",
            effective_channels: ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
            effective_diff_policy: "DIFF_ONLY",
            effective_snapshot_policy: "ON_JOIN",
            effective_compression: "NONE",
        });
        scriptedLiveClient.emitMessage("FULL_SNAPSHOT", {
            schema_version: "enqueteur_mbam_1",
            tick: 0,
            step_hash: "hash-0",
            state: { world: {} },
        });
        await flushAsyncWork();

        scriptedLiveClient.emitMessage("ERROR", {
            code: "INTERNAL_RUNTIME_ERROR",
            message: "fatal runtime failure",
            fatal: true,
        });

        expect(flow.getState()).toEqual({
            kind: "ERROR",
            code: "CONNECTION_FAILURE",
            message: "Live kernel error (INTERNAL_RUNTIME_ERROR): fatal runtime failure",
            recoverTo: "CASE_SELECT",
        });

        flow.destroy();
    });
});
