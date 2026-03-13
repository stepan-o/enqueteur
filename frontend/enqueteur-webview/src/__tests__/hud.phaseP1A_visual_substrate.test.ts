import { afterEach, describe, expect, it } from "vitest";

import { setLocale } from "../i18n";
import { WorldStore } from "../state/worldStore";
import { makeMbamSnapshot } from "./mbamFixtures";
import { useLocaleFixture } from "./testUtils/localeTestUtils";
import { mountHud } from "../ui/hud";

useLocaleFixture("en");

function flushUi(): Promise<void> {
    return new Promise((resolve) => window.setTimeout(resolve, 0));
}

afterEach(() => {
    document.body.innerHTML = "";
});

describe("P1A HUD visual substrate hardening", () => {
    it("uses class-based shell styling and rerenders localized chrome text", async () => {
        const store = new WorldStore();
        const hud = mountHud(store, undefined, { profile: "playtest" });
        document.body.appendChild(hud.root);

        store.applySnapshot(makeMbamSnapshot(4));
        store.setConnected(true);
        await flushUi();

        const root = document.querySelector<HTMLElement>(".hud-root");
        const panel = document.querySelector<HTMLElement>(".hud-panel-main");
        const feedPanel = document.querySelector<HTMLElement>(".hud-panel-feed");
        const title = document.querySelector<HTMLElement>(".hud-panel-title");
        const feedTitle = document.querySelector<HTMLElement>(".hud-feed-title");
        const dot = document.querySelector<HTMLElement>(".hud-status-dot");

        expect(root).not.toBeNull();
        expect(panel).not.toBeNull();
        expect(feedPanel).not.toBeNull();
        expect(root?.getAttribute("style")).toBeNull();
        expect(panel?.getAttribute("style")).toBeNull();
        expect(feedPanel?.getAttribute("style")).toBeNull();
        expect(dot?.dataset.status).toBe("live");
        expect(title?.textContent).toBe("Case Status");
        expect(feedTitle?.textContent).toBe("Case Feed");

        setLocale("fr");
        await flushUi();

        expect(title?.textContent).toBe("Etat Du Dossier");
        expect(feedTitle?.textContent).toBe("Flux Du Dossier");
        expect(panel?.textContent).toContain("Session");
    });
});
