import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mountAppFlow, type AppFlowOpts } from "../app/appFlow";
import {
    CaseLaunchError,
    type CaseLaunchClient,
    type CaseLaunchMetadata,
} from "../app/api/caseLaunchClient";
import type { EnqueteurLiveClientLike } from "../app/live/enqueteurLiveClient";

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

function makeIdleLiveClient(): EnqueteurLiveClientLike & {
    connect: ReturnType<typeof vi.fn>;
    disconnect: ReturnType<typeof vi.fn>;
    sendSubscribe: ReturnType<typeof vi.fn>;
} {
    const connect = vi.fn(() => {});
    const disconnect = vi.fn((_code?: number, _reason?: string) => {});
    const sendSubscribe = vi.fn(() => true);
    const onOpen = vi.fn((_handler: () => void) => () => {});
    const onClose = vi.fn((_handler: (event: CloseEvent) => void) => () => {});
    const onTransportError = vi.fn((_handler: (event: Event) => void) => () => {});
    const onProtocolError = vi.fn((_handler: unknown) => () => {});
    const onMessage = vi.fn((_msgType: unknown, _handler: unknown) => () => {});

    return {
        connect,
        disconnect,
        onOpen,
        onClose,
        onTransportError,
        onProtocolError,
        onMessage: onMessage as EnqueteurLiveClientLike["onMessage"],
        sendSubscribe,
    };
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

describe("Phase B3 case launch request flow", () => {
    it("calls backend launch request from MBAM case click and stores metadata", async () => {
        let resolveStartCase: (value: CaseLaunchMetadata) => void = () => {};
        const startCase = vi.fn(
            () =>
                new Promise<CaseLaunchMetadata>((resolve) => {
                    resolveStartCase = resolve;
                })
        );
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const liveClient = makeIdleLiveClient();
        const createLiveClient = vi.fn(() => liveClient);
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();

        expect(flow.getState()).toEqual({
            kind: "CONNECTING",
            caseId: "MBAM_01",
            phase: "CASE_LAUNCH",
        });

        expect(startCase).toHaveBeenCalledTimes(1);
        expect(startCase).toHaveBeenCalledWith(
            {
                caseId: "MBAM_01",
                seed: "A",
                difficultyProfile: "D0",
                mode: "playtest",
            },
            { signal: expect.any(AbortSignal) }
        );

        resolveStartCase(makeLaunchMetadata());
        await flushAsyncWork();

        expect(flow.getState()).toEqual({
            kind: "CONNECTING",
            caseId: "MBAM_01",
            phase: "SESSION_STARTUP",
        });
        expect(createLiveClient).toHaveBeenCalledTimes(1);
        expect(createLiveClient).toHaveBeenCalledWith(expect.objectContaining({
            runId: "run-123",
            wsUrl: "ws://localhost:7777/live?run_id=run-123",
            engineName: "enqueteur",
            schemaVersion: "enqueteur_mbam_1",
        }));
        expect(liveClient.connect).toHaveBeenCalledTimes(1);
        expect(flow.getLaunchMetadata()).toEqual(makeLaunchMetadata());
        expect(flow.getLaunchFailure()).toBeNull();

        flow.destroy();
    });

    it("routes launch failures into top-level ERROR state", async () => {
        const startCase = vi.fn(async () => {
            throw new Error("backend unavailable");
        });
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const createLiveClient = vi.fn(() => makeIdleLiveClient());
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();
        await flushAsyncWork();

        expect(flow.getState()).toEqual({
            kind: "ERROR",
            code: "LAUNCH_FAILURE",
            message: "Case launch failed: backend unavailable",
            recoverTo: "CASE_SELECT",
        });
        expect(flow.getLaunchMetadata()).toBeNull();
        expect(flow.getLaunchFailure()).toEqual({
            request: {
                caseId: "MBAM_01",
                seed: "A",
                difficultyProfile: "D0",
                mode: "playtest",
            },
            message: "Case launch failed: backend unavailable",
            code: "CASE_LAUNCH_FAILED",
            field: undefined,
            status: undefined,
            occurredAt: expect.any(String),
        });
        expect(createLiveClient).not.toHaveBeenCalled();

        flow.destroy();
    });

    it("routes invalid launch contract responses into startup incompatibility", async () => {
        const startCase = vi.fn(async () => {
            throw new CaseLaunchError("Expected 'schema_version' to be 'enqueteur_mbam_1'.", {
                status: 502,
                code: "INVALID_RESPONSE",
            });
        });
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const createLiveClient = vi.fn(() => makeIdleLiveClient());
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();
        await flushAsyncWork();

        expect(flow.getState()).toEqual({
            kind: "ERROR",
            code: "STARTUP_INCOMPATIBILITY",
            message: "Expected 'schema_version' to be 'enqueteur_mbam_1'.",
            recoverTo: "MAIN_MENU",
        });
        expect(flow.getLaunchMetadata()).toBeNull();
        expect(flow.getLaunchFailure()).toEqual({
            request: {
                caseId: "MBAM_01",
                seed: "A",
                difficultyProfile: "D0",
                mode: "playtest",
            },
            message: "Expected 'schema_version' to be 'enqueteur_mbam_1'.",
            code: "INVALID_RESPONSE",
            field: undefined,
            status: 502,
            occurredAt: expect.any(String),
        });
        expect(createLiveClient).not.toHaveBeenCalled();

        flow.destroy();
    });

    it("keeps backend reachability failures in relaunchable launch-failure flow", async () => {
        const startCase = vi.fn(async () => {
            throw new CaseLaunchError(
                "Could not reach backend launch endpoint at http://127.0.0.1:7777/api/cases/start.",
                {
                    status: 503,
                    code: "BACKEND_UNREACHABLE",
                }
            );
        });
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const createLiveClient = vi.fn(() => makeIdleLiveClient());
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CASE_SELECT" });
        clickFirstCaseCard();
        await flushAsyncWork();

        expect(flow.getState()).toEqual({
            kind: "ERROR",
            code: "LAUNCH_FAILURE",
            message: "Could not reach backend launch endpoint at http://127.0.0.1:7777/api/cases/start.",
            recoverTo: "CASE_SELECT",
        });
        expect(flow.getLaunchFailure()).toEqual({
            request: {
                caseId: "MBAM_01",
                seed: "A",
                difficultyProfile: "D0",
                mode: "playtest",
            },
            message: (
                "Could not reach backend launch endpoint at http://127.0.0.1:7777/api/cases/start."
            ),
            code: "BACKEND_UNREACHABLE",
            field: undefined,
            status: 503,
            occurredAt: expect.any(String),
        });
        expect(createLiveClient).not.toHaveBeenCalled();

        flow.destroy();
    });

    it("treats non-launch connecting phases without metadata as an unexpected-state error", async () => {
        const startCase = vi.fn(async () => makeLaunchMetadata());
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const createLiveClient = vi.fn(() => makeIdleLiveClient());
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
            createLiveClient,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "CONNECTING", caseId: "MBAM_01", phase: "SESSION_STARTUP" });
        await flushAsyncWork();

        expect(flow.getState()).toEqual({
            kind: "ERROR",
            code: "UNEXPECTED_STATE",
            message: "Launch metadata is missing; return to case selection and relaunch.",
            recoverTo: "CASE_SELECT",
        });
        expect(createLiveClient).not.toHaveBeenCalled();

        flow.destroy();
    });
});
