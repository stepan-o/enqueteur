import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mountAppFlow, type AppFlowOpts } from "../app/appFlow";
import type { ViewerHandle } from "../app/boot";

type FakeViewer = ViewerHandle & {
    startOffline: ReturnType<typeof vi.fn>;
    startLive: ReturnType<typeof vi.fn>;
    stop: ReturnType<typeof vi.fn>;
    setVisible: ReturnType<typeof vi.fn>;
    setDevControlsVisible: ReturnType<typeof vi.fn>;
    setHudVisible: ReturnType<typeof vi.fn>;
};

function makeMountEl(): HTMLElement {
    const mountEl = document.createElement("div");
    document.body.appendChild(mountEl);
    return mountEl;
}

function makeFakeViewer(): FakeViewer {
    const startOffline = vi.fn(async (_baseUrl?: string, _speed?: number) => {});
    const startLive = vi.fn((_wsUrl?: string) => {});
    const stop = vi.fn(() => {});
    const setVisible = vi.fn((_visible: boolean) => {});
    const setDevControlsVisible = vi.fn((_visible: boolean) => {});
    const setHudVisible = vi.fn((_visible: boolean) => {});

    return {
        startOffline,
        startLive,
        stop,
        setVisible,
        setDevControlsVisible,
        setHudVisible,
    } as FakeViewer;
}

async function flushAsyncWork(): Promise<void> {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
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

describe("Phase A5 app flow live shell gate", () => {
    it("does not mount gameplay shell during pre-game states", async () => {
        const viewer = makeFakeViewer();
        const createLiveViewer: NonNullable<AppFlowOpts["createLiveViewer"]> = vi.fn(
            async (_mountEl: HTMLElement) => viewer
        );
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            createLiveViewer,
        });

        flow.transition({ kind: "MAIN_MENU" });
        flow.transition({ kind: "CASE_SELECT" });
        flow.transition({ kind: "CONNECTING", caseId: "MBAM_01", phase: "CASE_LAUNCH" });

        await flushAsyncWork();
        expect(createLiveViewer).not.toHaveBeenCalled();

        flow.destroy();
    });

    it("mounts gameplay shell only after entering LIVE_GAME", async () => {
        const viewer = makeFakeViewer();
        const createLiveViewer: NonNullable<AppFlowOpts["createLiveViewer"]> = vi.fn(
            async (_mountEl: HTMLElement) => viewer
        );
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            createLiveViewer,
        });

        flow.transition({ kind: "LIVE_GAME", caseId: "MBAM_01" });
        await flushAsyncWork();

        expect(createLiveViewer).toHaveBeenCalledTimes(1);
        expect(createLiveViewer).toHaveBeenCalledWith(expect.any(HTMLElement));
        expect(viewer.setVisible).toHaveBeenCalledWith(true);

        flow.transition({ kind: "MAIN_MENU" });
        expect(viewer.setVisible).toHaveBeenLastCalledWith(false);

        flow.destroy();
        expect(viewer.stop).toHaveBeenCalledTimes(1);
    });
});
