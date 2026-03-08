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
        const snapshot = makeMbamSnapshot(2);
        snapshot.state.dialogue?.recent_turns.push({
            turn_index: 1,
            scene_id: "S1",
            npc_id: "elodie",
            intent_id: "summarize_understanding",
            status: "repair",
            code: "summary_insufficient_facts",
            outcome: "repair",
            response_mode: "repair",
            revealed_fact_ids: [],
            trust_delta: 0,
            stress_delta: 0,
            repair_response_mode: "sentence_stem",
            summary_check_code: "summary_insufficient_facts",
        });
        store.applySnapshot(snapshot);

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
        expect(panel?.textContent).toContain("Summary & Hint Ladder");
        expect(panel?.textContent).toContain("Hint ladder");
        expect(panel?.textContent).toContain("Soft Hint - current");
        expect(panel?.textContent).toContain("Sentence Stem - locked");
        expect(panel?.textContent).toContain("Prompt:");
        expect(panel?.textContent).toContain("Summary missing enough corroborated facts.");
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
        expect(panel?.textContent).toContain("Mini-Exercises");
        expect(panel?.textContent).toContain("MG1 Wall Label Reading");
        expect(panel?.textContent).toContain("MG2 Badge Log Read");
        expect(panel?.textContent).toContain("MG3 Receipt Reading");
        expect(panel?.textContent).toContain("MG4 Torn Note Reconstruction");
    });

    it("evaluates MG1-MG4 notebook widgets deterministically", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(4));

        const notebook = mountNotebookPanel(store);
        document.body.appendChild(notebook.root);
        const panel = notebook.root.querySelector(".notebook-panel");
        const cards = Array.from(notebook.root.querySelectorAll<HTMLElement>(".notebook-minigame"));

        const mg1 = cards.find((card) => card.textContent?.includes("MG1 Wall Label Reading"));
        const mg2 = cards.find((card) => card.textContent?.includes("MG2 Badge Log Read"));
        const mg3 = cards.find((card) => card.textContent?.includes("MG3 Receipt Reading"));
        const mg4 = cards.find((card) => card.textContent?.includes("MG4 Torn Note Reconstruction"));
        expect(mg1).toBeTruthy();
        expect(mg2).toBeTruthy();
        expect(mg3).toBeTruthy();
        expect(mg4).toBeTruthy();

        const mg1Inputs = Array.from(mg1!.querySelectorAll<HTMLInputElement>("input.notebook-minigame-input"));
        mg1Inputs[0]!.value = "Le Medaillon des Voyageurs";
        mg1Inputs[0]!.dispatchEvent(new Event("input"));
        mg1Inputs[1]!.value = "1898";
        mg1Inputs[1]!.dispatchEvent(new Event("input"));

        const mg2Select = mg2!.querySelector<HTMLSelectElement>("select.notebook-minigame-input");
        const mg2Time = mg2!.querySelector<HTMLInputElement>("input.notebook-minigame-input");
        expect(mg2Select).toBeTruthy();
        expect(mg2Time).toBeTruthy();
        mg2Select!.value = "MBAM-STF-04";
        mg2Select!.dispatchEvent(new Event("change"));
        mg2Time!.value = "17:58";
        mg2Time!.dispatchEvent(new Event("input"));

        const mg3Inputs = Array.from(mg3!.querySelectorAll<HTMLInputElement>("input.notebook-minigame-input"));
        mg3Inputs[0]!.value = "17:52";
        mg3Inputs[0]!.dispatchEvent(new Event("input"));
        mg3Inputs[1]!.value = "cafe filtre";
        mg3Inputs[1]!.dispatchEvent(new Event("input"));

        const mg4Selects = Array.from(mg4!.querySelectorAll<HTMLSelectElement>("select.notebook-minigame-input"));
        expect(mg4Selects.length).toBe(3);
        mg4Selects[0]!.value = "chariot";
        mg4Selects[0]!.dispatchEvent(new Event("change"));
        mg4Selects[1]!.value = "livraison";
        mg4Selects[1]!.dispatchEvent(new Event("change"));
        mg4Selects[2]!.value = "17h58";
        mg4Selects[2]!.dispatchEvent(new Event("change"));

        mg1!.querySelectorAll<HTMLButtonElement>(".notebook-minigame-btn")[0]!.click();
        mg2!.querySelectorAll<HTMLButtonElement>(".notebook-minigame-btn")[0]!.click();
        mg3!.querySelectorAll<HTMLButtonElement>(".notebook-minigame-btn")[0]!.click();
        mg4!.querySelectorAll<HTMLButtonElement>(".notebook-minigame-btn")[0]!.click();
        await flushUi();

        expect(panel?.textContent).toContain("Correct (2/2).");
        expect(panel?.textContent).toContain("Correct (3/3).");
    });
});
