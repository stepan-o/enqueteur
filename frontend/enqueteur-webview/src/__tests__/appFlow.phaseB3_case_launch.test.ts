import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mountAppFlow, type AppFlowOpts } from "../app/appFlow";
import type { CaseLaunchClient, CaseLaunchMetadata } from "../app/api/caseLaunchClient";

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
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
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
        expect(flow.getLaunchMetadata()).toEqual(makeLaunchMetadata());

        flow.destroy();
    });

    it("routes launch failures into top-level ERROR state", async () => {
        const startCase = vi.fn(async () => {
            throw new Error("backend unavailable");
        });
        const caseLaunchClient: CaseLaunchClient = { startCase };
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            caseLaunchClient,
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

        flow.destroy();
    });
});
