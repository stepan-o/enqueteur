import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mountAppFlow, type AppFlowOpts } from "../app/appFlow";
import type { ViewerHandle } from "../app/boot";
import { LocaleStore, setLocale } from "../i18n";
import { WorldStore } from "../state/worldStore";
import { mountDialoguePanel } from "../ui/dialoguePanel";
import { mountInspectPanel } from "../ui/inspectPanel";
import { mountNotebookPanel } from "../ui/notebookPanel";
import { mountResolutionPanel } from "../ui/resolutionPanel";
import { makeMbamSnapshot } from "./mbamFixtures";

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
    setLocale("en");
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
        cb(performance.now());
        return 1;
    });
});

afterEach(() => {
    setLocale("en");
    vi.restoreAllMocks();
    document.body.innerHTML = "";
});

describe("Phase L2 localized UI migration coverage", () => {
    it("renders key pregame surfaces in French under explicit locale", async () => {
        const localeStore = new LocaleStore("fr");
        const flow = mountAppFlow({
            mountEl: makeMountEl(),
            loadingDurationMs: 10_000,
            localeStore,
        } satisfies AppFlowOpts);

        flow.transition({ kind: "MAIN_MENU" });
        await flushAsyncWork();
        expect(document.body.textContent).toContain("Demarrer Le Dossier");

        flow.transition({ kind: "CASE_SELECT" });
        await flushAsyncWork();
        expect(document.body.textContent).toContain("Choisir Un Dossier");
        expect(document.body.textContent).toContain("Retour Au Menu");
        expect(document.body.textContent).toContain("Parcours demo par defaut:");

        flow.transition({ kind: "CONNECTING", caseId: "MBAM_01", phase: "CASE_LAUNCH" });
        await flushAsyncWork();
        expect(document.body.textContent).toContain("Entree Dans Le Dossier");
        expect(document.body.textContent).toContain("Preparation de Le Petit Vol du Musee");
        expect(document.body.textContent).toContain("Ouverture du dossier");
        expect(document.body.textContent).toContain("Retour Aux Dossiers");

        flow.destroy();
    });

    it("rerenders top-level live chrome labels when locale changes", async () => {
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

        expect(document.body.textContent).toContain("Back To Cases");
        expect(document.body.textContent).toContain("Main Menu");

        const { fr } = findLocaleButtons();
        fr.click();
        await flushAsyncWork();

        expect(localeStore.getLocale()).toBe("fr");
        expect(document.body.textContent).toContain("Retour Aux Dossiers");
        expect(document.body.textContent).toContain("Menu Principal");

        flow.destroy();
    });

    it("rerenders selected in-game panel headers from EN to FR", () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(1));

        const inspect = mountInspectPanel(store);
        inspect.setSelection({ kind: "object", id: 3002 });

        const dialogue = mountDialoguePanel(store);
        dialogue.setInspectSelection({ kind: "room", id: 1 });

        const notebook = mountNotebookPanel(store);
        const resolution = mountResolutionPanel(store);

        document.body.append(inspect.root, dialogue.root, notebook.root, resolution.root);

        expect(document.body.textContent).toContain("Investigation Actions");
        expect(document.body.textContent).toContain("Choose Your Line");
        expect(document.body.textContent).toContain("Case Notes");
        expect(document.body.textContent).toContain("Final Decision");

        setLocale("fr");

        expect(document.body.textContent).toContain("Actions D'Enquete");
        expect(document.body.textContent).toContain("Choisissez Votre Replique");
        expect(document.body.textContent).toContain("Notes Du Dossier");
        expect(document.body.textContent).toContain("Decision Finale");
    });
});
