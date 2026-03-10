import { afterEach, describe, expect, it } from "vitest";

import { mountDialoguePanel } from "../ui/dialoguePanel";
import { mountInspectPanel } from "../ui/inspectPanel";
import { mountNotebookPanel } from "../ui/notebookPanel";
import { mountResolutionPanel } from "../ui/resolutionPanel";
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
        expect(panel?.textContent).toContain("Interaction");
        expect(panel?.textContent).toContain("Field Prompt");
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
            presentation_source: "adapter",
            presentation_reason_code: "adapter_ok",
            presentation_metadata: ["mode:repair", "source:style_mbam_v1"],
            npc_utterance_text: "Très bien. Restons précis.",
            short_rephrase_line: "Essaie avec une phrase guide simple.",
            hint_line: "Indice: garde la structure qui, où, quand.",
            summary_prompt_line: "Fais un court résumé en français avant de continuer.",
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
        expect(panel?.textContent).toContain("npc: Très bien. Restons précis.");
        expect(panel?.textContent).toContain("rephrase:Essaie avec une phrase guide simple.");
        expect(panel?.textContent).toContain("summary_prompt:Fais un court résumé en français avant de continuer.");
        expect(panel?.textContent).toContain("hint:Indice: garde la structure qui, où, quand.");
        expect(panel?.textContent).toContain("presentation:adapter");
        expect(panel?.textContent).toContain("presentation_meta:[mode:repair, source:style_mbam_v1]");

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
        expect(panel?.textContent).toContain("Case Brief");
        expect(panel?.textContent).toContain("Start Here");
        expect(panel?.textContent).toContain("Inspect the Display Case and Wall Label in the gallery.");
        expect(panel?.textContent).toContain("Current lead:");
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

    it("renders deterministic D1 hint-ladder constraints without English bypass", () => {
        const store = new WorldStore();
        const snapshot = makeMbamSnapshot(5);
        if (!snapshot.state.dialogue?.learning) {
            throw new Error("fixture must include dialogue learning state");
        }
        snapshot.state.dialogue.active_scene_id = "S1";
        snapshot.state.dialogue.learning.difficulty_profile = "D1";
        snapshot.state.dialogue.learning.current_hint_level = "rephrase_choice";
        snapshot.state.dialogue.learning.scaffolding_policy = {
            ...snapshot.state.dialogue.learning.scaffolding_policy,
            scene_id: "S1",
            current_hint_level: "rephrase_choice",
            current_hint_rank: 2,
            allowed_hint_levels: ["soft_hint", "sentence_stem", "rephrase_choice"],
            recommended_mode: "rephrase_choice",
            english_meta_allowed: false,
            french_action_required: true,
            reason_code: "summary_pressure_escalation",
            soft_hint_key: "hint:s1_incident_scope",
            sentence_stem_key: "stem:s1_polite_incident",
            rephrase_set_id: "rephrase:s1_incident_core",
            english_meta_key: null,
            prompt_generosity: "medium",
            confirmation_strength: "compact",
            summary_strictness: "strict",
            language_support_level: "fr_primary",
            target_minigame_id: "MG1_LABEL_READING",
        };

        store.applySnapshot(snapshot);
        const dialogue = mountDialoguePanel(store);
        document.body.appendChild(dialogue.root);
        dialogue.setInspectSelection({ kind: "room", id: 1 });

        const panel = dialogue.root.querySelector(".dialogue-panel");
        expect(panel?.textContent).toContain("Difficulty");
        expect(panel?.textContent).toContain("D1");
        expect(panel?.textContent).toContain("FR required");
        expect(panel?.textContent).toContain("yes");
        expect(panel?.textContent).toContain("Meta EN help");
        expect(panel?.textContent).toContain("no");
        expect(panel?.textContent).toContain("English Meta-Help - locked");
        expect(panel?.textContent).toContain("Choose one:");
    });

    it("uses compact minigame feedback and respects projected gate blocking", async () => {
        const store = new WorldStore();
        const snapshot = makeMbamSnapshot(6);
        if (!snapshot.state.dialogue?.learning) {
            throw new Error("fixture must include dialogue learning state");
        }
        snapshot.state.dialogue.learning.scaffolding_policy.confirmation_strength = "compact";
        const mg2 = snapshot.state.dialogue.learning.minigames.find((row) => row.minigame_id === "MG2_BADGE_LOG");
        if (!mg2) throw new Error("fixture must include MG2 learning state");
        mg2.gate_open = false;
        mg2.gate_code = "wait_for_badge_logs";
        mg2.status = "not_started";
        mg2.attempt_count = 0;
        mg2.completed = false;
        mg2.score = 0;
        store.applySnapshot(snapshot);

        const notebook = mountNotebookPanel(store);
        document.body.appendChild(notebook.root);
        const panel = notebook.root.querySelector(".notebook-panel");
        const cards = Array.from(notebook.root.querySelectorAll<HTMLElement>(".notebook-minigame"));
        const mg1Card = cards.find((card) => card.textContent?.includes("MG1 Wall Label Reading"));
        const mg2Card = cards.find((card) => card.textContent?.includes("MG2 Badge Log Read"));
        expect(mg1Card).toBeTruthy();
        expect(mg2Card).toBeTruthy();

        const mg1Inputs = Array.from(mg1Card!.querySelectorAll<HTMLInputElement>("input.notebook-minigame-input"));
        mg1Inputs[0]!.value = "wrong";
        mg1Inputs[0]!.dispatchEvent(new Event("input"));
        mg1Inputs[1]!.value = "0000";
        mg1Inputs[1]!.dispatchEvent(new Event("input"));
        mg1Card!.querySelectorAll<HTMLButtonElement>(".notebook-minigame-btn")[0]!.click();
        await flushUi();

        const mg2Submit = mg2Card!.querySelectorAll<HTMLButtonElement>(".notebook-minigame-btn")[0]!;
        expect(mg2Submit.disabled).toBe(true);
        expect(panel?.textContent).toContain("Incorrect. Retry.");
    });

    it("disables local minigame scoring when live dispatch fallback is disabled", async () => {
        const store = new WorldStore();
        const snapshot = makeMbamSnapshot(6);
        if (!snapshot.state.dialogue?.learning) {
            throw new Error("fixture must include dialogue learning state");
        }
        snapshot.state.dialogue.learning.scaffolding_policy.confirmation_strength = "compact";
        store.applySnapshot(snapshot);

        const notebook = mountNotebookPanel(store, {
            allowLocalEvaluation: () => false,
        });
        document.body.appendChild(notebook.root);
        const panel = notebook.root.querySelector(".notebook-panel");
        const cards = Array.from(notebook.root.querySelectorAll<HTMLElement>(".notebook-minigame"));
        const mg1Card = cards.find((card) => card.textContent?.includes("MG1 Wall Label Reading"));
        expect(mg1Card).toBeTruthy();

        const mg1Inputs = Array.from(mg1Card!.querySelectorAll<HTMLInputElement>("input.notebook-minigame-input"));
        mg1Inputs[0]!.value = "Le Medaillon des Voyageurs";
        mg1Inputs[0]!.dispatchEvent(new Event("input"));
        mg1Inputs[1]!.value = "1898";
        mg1Inputs[1]!.dispatchEvent(new Event("input"));
        mg1Card!.querySelectorAll<HTMLButtonElement>(".notebook-minigame-btn")[0]!.click();
        await flushUi();

        expect(panel?.textContent).toContain("Live minigame dispatch is unavailable.");
        expect(panel?.textContent).not.toContain("Correct (2/2).");
    });

    it("renders terminal recap details for resolved MBAM outcomes", () => {
        const store = new WorldStore();
        const snapshot = makeMbamSnapshot(7);
        if (!snapshot.state.case_recap) {
            throw new Error("fixture must include case recap projection");
        }
        if (!snapshot.state.case_outcome) {
            throw new Error("fixture must include case outcome projection");
        }
        snapshot.state.case_outcome.primary_outcome = "best_outcome";
        snapshot.state.case_outcome.terminal = true;
        snapshot.state.case_outcome.best_outcome = true;
        snapshot.state.case_outcome.best_outcome_awarded = true;
        snapshot.state.case_outcome.continuity_flags = [
            "continuity:quiet_recovery",
            "continuity:strong_key_trust",
        ];
        snapshot.state.case_recap = {
            ...snapshot.state.case_recap,
            available: true,
            final_outcome_type: "best_outcome",
            resolution_path: "recovery",
            resolution_path_components: ["recovery", "accusation"],
            key_fact_ids: ["N3", "N4", "N8"],
            key_evidence_ids: ["E2_CAFE_RECEIPT", "E3_METHOD_TRACE"],
            key_action_flags: ["action:recover_medallion", "action:accuse_samira"],
            contradiction_used: true,
            contradiction_action_flags: ["action:state_contradiction_N3_N4"],
            contradiction_requirement_satisfied: true,
            relationship_result_flags: ["rel_elodie_positive", "rel_marc_positive", "continuity:strong_key_trust"],
            soft_fail: {
                triggered: false,
                latched: false,
                trigger_conditions: [],
                item_left_building: false,
            },
            best_outcome: {
                awarded: true,
                quiet_recovery: true,
                no_public_escalation: true,
                strong_key_trust: true,
            },
            continuity_flags: ["continuity:quiet_recovery", "continuity:strong_key_trust"],
        };
        store.applySnapshot(snapshot);

        const resolution = mountResolutionPanel(store);
        document.body.appendChild(resolution.root);
        const panel = resolution.root.querySelector(".resolution-panel");

        expect(panel?.textContent).toContain("Decision Board");
        expect(panel?.textContent).toContain("best_outcome");
        expect(panel?.textContent).toContain("recovery");
        expect(panel?.textContent).toContain("resolved");
        expect(panel?.textContent).toContain("N3 Badge log 17h58");
        expect(panel?.textContent).toContain("E2 Cafe Receipt");
        expect(panel?.textContent).toContain("Best Outcome Markers");
        expect(panel?.textContent).toContain("quiet_recovery");
    });
});
