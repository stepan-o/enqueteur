import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mountAppFlow, type AppFlowOpts } from "../app/appFlow";
import type { ViewerHandle } from "../app/boot";
import { LocaleStore } from "../i18n";

type FakeViewer = ViewerHandle & {
    stop: ReturnType<typeof vi.fn>;
    setVisible: ReturnType<typeof vi.fn>;
};

function makeMountEl(): HTMLElement {
    const mountEl = document.createElement("div");
    document.body.appendChild(mountEl);
    return mountEl;
}

function makeFakeViewer(): FakeViewer {
    return {
        startOffline: vi.fn(async () => {}),
        startLive: vi.fn(() => {}),
        stop: vi.fn(() => {}),
        setVisible: vi.fn(() => {}),
        setDevControlsVisible: vi.fn(() => {}),
        setHudVisible: vi.fn(() => {}),
    } as FakeViewer;
}

async function flushAsyncWork(): Promise<void> {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
}

function findLocaleButtons(): {
    en: HTMLButtonElement;
    fr: HTMLButtonElement;
} {
    const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>(".flow-locale-btn"));
    const en = buttons.find((button) => button.textContent?.trim() === "EN");
    const fr = buttons.find((button) => button.textContent?.trim() === "FR");
    if (!en || !fr) throw new Error("locale buttons not found");
    return { en, fr };
}

beforeEach(() => {
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
        cb(performance.now());
        return 1;
    });
});

afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
});

describe("Phase L1 visible locale toggle", () => {
    it("is visible in main menu and rerenders menu copy immediately", async () => {
        const localeStore = new LocaleStore("en");
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            localeStore,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "MAIN_MENU" });
        await flushAsyncWork();

        const switchRoot = document.querySelector<HTMLElement>(".flow-locale-switch");
        expect(switchRoot).not.toBeNull();
        expect(document.body.textContent).toContain("Start Case");

        const { fr, en } = findLocaleButtons();
        expect(en.getAttribute("aria-pressed")).toBe("true");

        fr.click();
        await flushAsyncWork();

        expect(localeStore.getLocale()).toBe("fr");
        expect(document.body.textContent).toContain("Demarrer Le Dossier");
        expect(fr.getAttribute("aria-pressed")).toBe("true");
        expect(en.getAttribute("aria-pressed")).toBe("false");

        flow.destroy();
    });

    it("remains visible in live gameplay and updates live chrome text", async () => {
        const localeStore = new LocaleStore("en");
        const viewer = makeFakeViewer();
        const createLiveViewer: NonNullable<AppFlowOpts["createLiveViewer"]> = vi.fn(
            async () => viewer
        );
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            localeStore,
            createLiveViewer,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "LIVE_GAME", caseId: "MBAM_01" });
        await flushAsyncWork();

        const switchRoot = document.querySelector<HTMLElement>(".flow-locale-switch");
        expect(switchRoot).not.toBeNull();
        expect(document.body.textContent).toContain("Main Menu");

        const { fr } = findLocaleButtons();
        fr.click();
        await flushAsyncWork();

        expect(localeStore.getLocale()).toBe("fr");
        expect(document.body.textContent).toContain("Menu Principal");

        flow.destroy();
    });
});
