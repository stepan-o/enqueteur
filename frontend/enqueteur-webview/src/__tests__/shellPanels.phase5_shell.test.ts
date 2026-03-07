import { afterEach, describe, expect, it } from "vitest";

import { mountDialoguePanel } from "../ui/dialoguePanel";
import { mountInspectPanel } from "../ui/inspectPanel";
import { mountNotebookPanel } from "../ui/notebookPanel";
import { WorldStore } from "../state/worldStore";
import { makeMbamSnapshot } from "./mbamFixtures";

function flushUi(): Promise<void> {
    return new Promise((resolve) => window.setTimeout(resolve, 0));
}

afterEach(() => {
    document.body.innerHTML = "";
});

describe("Phase 5 shell panel rendering", () => {
    it("renders inspection actions and last action feedback for MBAM objects", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(1));

        const inspect = mountInspectPanel(store, {
            canDispatchInvestigationAction: () => true,
            dispatchInvestigationAction: async () => ({
                status: "accepted",
                code: "projection_affordance_observed",
                summary: "Projected state confirms this affordance was observed.",
                revealed_fact_ids: ["N7"],
                revealed_evidence_ids: ["E1_TORN_NOTE"],
            }),
        });
        document.body.appendChild(inspect.root);
        inspect.setSelection({ kind: "object", id: 3002 });

        const panel = inspect.root.querySelector(".inspect-panel");
        expect(panel?.textContent).toContain("MBAM Investigation");
        expect(panel?.textContent).toContain("O1_DISPLAY_CASE");

        const buttons = inspect.root.querySelectorAll<HTMLButtonElement>(".inspect-action-btn");
        expect(buttons.length).toBeGreaterThanOrEqual(3);
        buttons[0]?.click();
        await flushUi();

        expect(panel?.textContent).toContain("Last Action Result");
        expect(panel?.textContent).toContain("projection_affordance_observed");
        expect(panel?.textContent).toContain("accepted");
    });

    it("renders structured dialogue state, transcript, and NPC state-card fields", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(2));

        const dialogue = mountDialoguePanel(store, {
            canDispatchDialogueTurn: () => true,
            dispatchDialogueTurn: async () => ({
                status: "accepted",
                code: "summary_ok",
                summary: "Summary accepted",
                revealed_fact_ids: ["N3"],
            }),
        });
        document.body.appendChild(dialogue.root);
        dialogue.setInspectSelection({ kind: "room", id: 1 });

        const panel = dialogue.root.querySelector(".dialogue-panel");
        expect(panel?.textContent).toContain("NPC State Card");
        expect(panel?.textContent).toContain("Scaffolding");
        expect(panel?.textContent).toContain("Hint level");
        expect(panel?.textContent).toContain("Emotion");
        expect(panel?.textContent).toContain("Stance");
        expect(panel?.textContent).toContain("Trust trend");
        expect(panel?.textContent).toContain("Recent Structured Turns");

        const submit = dialogue.root.querySelector<HTMLButtonElement>(".dialogue-submit");
        expect(submit?.disabled).toBe(false);
        submit?.click();
        await flushUi();

        expect(panel?.textContent).toContain("Last Submission");
        expect(panel?.textContent).toContain("summary_ok");
    });

    it("renders notebook evidence/fact/contradiction/timeline sections from projection", () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(3));

        const notebook = mountNotebookPanel(store);
        document.body.appendChild(notebook.root);
        const panel = notebook.root.querySelector(".notebook-panel");

        expect(panel?.textContent).toContain("Evidence Tray");
        expect(panel?.textContent).toContain("E2 Cafe Receipt");
        expect(panel?.textContent).toContain("Fact Visibility");
        expect(panel?.textContent).toContain("N1");
        expect(panel?.textContent).toContain("Contradictions");
        expect(panel?.textContent).toContain("Unlockable edges");
        expect(panel?.textContent).toContain("Timeline Clues");
    });
});
