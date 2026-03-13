import { afterEach, describe, expect, it } from "vitest";

import { mountDialoguePanel } from "../ui/dialoguePanel";
import { mountInspectPanel } from "../ui/inspectPanel";
import { mountNotebookPanel } from "../ui/notebookPanel";
import { mountResolutionPanel } from "../ui/resolutionPanel";
import { WorldStore } from "../state/worldStore";
import { makeMbamSnapshot } from "./mbamFixtures";
import { trFor, useLocaleFixture } from "./testUtils/localeTestUtils";

const tr = trFor("en");
useLocaleFixture("en");

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
        expect(panel?.textContent).toContain(tr("inspect.section.investigation_actions"));
        expect(panel?.textContent).toContain(tr("inspect.section.field_prompt"));
        expect(panel?.textContent).toContain("O1_DISPLAY_CASE");
        expect(panel?.textContent).toContain(tr("inspect.line.location_hint"));
        expect(panel?.textContent).toContain(tr("inspect.info.new_lead", { hint: "" }).trim());

        const buttons = inspect.root.querySelectorAll<HTMLButtonElement>(".inspect-action-btn");
        expect(buttons.length).toBeGreaterThanOrEqual(3);
        buttons[0]?.click();
        await flushUi();

        expect(panel?.textContent).toContain(tr("inspect.section.latest_result"));
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
        expect(panel?.textContent).toContain(tr("dialogue.section.character_read"));
        expect(panel?.textContent).toContain(tr("dialogue.section.conversation_support"));
        expect(panel?.textContent).toContain(tr("dialogue.section.summary_guidance"));
        expect(panel?.textContent).toContain(tr("dialogue.section.contradiction_clues"));
        expect(panel?.textContent).toContain(tr("dialogue.hint_track.title", { level: "", profile: "" }).split("(")[0]?.trim() ?? "");
        expect(panel?.textContent).toContain(`${tr("dialogue.hint_level.soft_hint")} - ${tr("dialogue.hint_state.current")}`);
        expect(panel?.textContent).toContain(`${tr("dialogue.hint_level.sentence_stem")} - ${tr("dialogue.hint_state.locked")}`);
        expect(panel?.textContent).toContain(tr("dialogue.summary.prompt_line", { prompt: "" }).trim());
        expect(panel?.textContent).toContain(tr("dialogue.summary_code.summary_insufficient_facts"));
        expect(panel?.textContent).toContain(tr("dialogue.line.hint_level"));
        expect(panel?.textContent).toContain(tr("dialogue.npc_line.emotion"));
        expect(panel?.textContent).toContain(tr("dialogue.npc_line.stance"));
        expect(panel?.textContent).toContain(tr("dialogue.npc_line.trust_trend"));
        expect(panel?.textContent).toContain(tr("dialogue.section.recent_turns"));
        expect(panel?.textContent).toContain(tr("dialogue.info.facts_you_can_cite", { facts: "" }).trim());
        expect(panel?.textContent).toContain(tr("dialogue.info.evidence_you_can_cite", { evidence: "" }).trim());
        expect(panel?.textContent).toContain("NPC: Très bien. Restons précis.");
        expect(panel?.textContent).toContain("rephrase:Essaie avec une phrase guide simple.");
        expect(panel?.textContent).toContain("summary_prompt:Fais un court résumé en français avant de continuer.");
        expect(panel?.textContent).toContain("hint:Indice: garde la structure qui, où, quand.");
        expect(panel?.textContent).toContain("presentation:adapter");
        expect(panel?.textContent).toContain("presentation_meta:[mode:repair, source:style_mbam_v1]");

        const submit = dialogue.root.querySelector<HTMLButtonElement>(".dialogue-submit");
        expect(submit?.disabled).toBe(false);
        submit?.click();
        await flushUi();

        expect(panel?.textContent).toContain(tr("dialogue.section.latest_attempt"));
        expect(panel?.textContent).toContain("summary_ok");
    });

    it("renders notebook evidence/fact/contradiction/timeline sections from projection", () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(3));

        const notebook = mountNotebookPanel(store);
        document.body.appendChild(notebook.root);
        const panel = notebook.root.querySelector(".notebook-panel");

        expect(panel?.textContent).toContain(tr("notebook.section.evidence_tray"));
        expect(panel?.textContent).toContain(tr("notebook.section.case_brief"));
        expect(panel?.textContent).toContain(tr("notebook.section.case_setup"));
        expect(panel?.textContent).toContain(tr("notebook.setup.what_happened", { incident: tr("mbam.case.incident") }));
        expect(panel?.textContent).toContain(tr("notebook.section.start_here"));
        expect(panel?.textContent).toContain(tr("mbam.onboarding.step.inspect_starters"));
        expect(panel?.textContent).toContain(tr("notebook.current_lead", { lead: "" }).split(":")[0] ?? "");
        expect(panel?.textContent).toContain(tr("mbam.playtest.title"));
        expect(panel?.textContent).toContain(tr("mbam.playtest.step.starter_investigation"));
        expect(panel?.textContent).toContain(tr("mbam.playtest.current.next", { label: "" }).split(":")[0] ?? "");
        expect(panel?.textContent).toContain(tr("notebook.section.key_object_leads"));
        expect(panel?.textContent).toContain("E2 Cafe Receipt");
        expect(panel?.textContent).toContain(tr("notebook.section.known_facts"));
        expect(panel?.textContent).toContain("N1");
        expect(panel?.textContent).toContain(tr("notebook.section.contradictions"));
        expect(panel?.textContent).toContain(tr("notebook.contradictions.unlockable_edges"));
        expect(panel?.textContent).toContain(tr("notebook.contradictions.where_to_use"));
        expect(panel?.textContent).toContain(tr("notebook.section.timeline_clues"));
        expect(panel?.textContent).toContain(tr("notebook.section.field_exercises"));
        expect(panel?.textContent).toContain(tr("notebook.mg1.title"));
        expect(panel?.textContent).toContain(tr("notebook.mg2.title"));
        expect(panel?.textContent).toContain(tr("notebook.mg3.title"));
        expect(panel?.textContent).toContain(tr("notebook.mg4.title"));
    });

    it("demotes internal-only notebook guidance in demo presentation profile", () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(3));

        const notebook = mountNotebookPanel(store, {
            presentationProfile: "demo",
        });
        document.body.appendChild(notebook.root);
        const panel = notebook.root.querySelector(".notebook-panel");

        expect(panel?.textContent).toContain(tr("notebook.section.case_brief"));
        expect(panel?.textContent).toContain(tr("notebook.section.key_object_leads"));
        expect(panel?.textContent).not.toContain(tr("mbam.playtest.title"));
        expect(panel?.textContent).not.toContain(tr("notebook.line.truth_epoch"));
    });

    it("keeps demo shell guidance readable while preserving key action reachability", async () => {
        const store = new WorldStore();
        const snapshot = makeMbamSnapshot(8);
        if (!snapshot.state.dialogue || !snapshot.state.case_outcome || !snapshot.state.case_recap) {
            throw new Error("fixture must include dialogue/outcome/recap projections");
        }

        snapshot.state.dialogue.recent_turns = [];
        snapshot.state.case_outcome.primary_outcome = "recovery_success";
        snapshot.state.case_outcome.terminal = true;
        snapshot.state.case_outcome.recovery_success = true;
        snapshot.state.case_outcome.accusation_success = false;
        snapshot.state.case_outcome.soft_fail = false;
        snapshot.state.case_recap = {
            ...snapshot.state.case_recap,
            available: true,
            final_outcome_type: "recovery_success",
            resolution_path: "recovery",
            key_fact_ids: ["N1", "N3", "N4"],
            key_evidence_ids: ["E2_CAFE_RECEIPT"],
            key_action_flags: ["action:recover_medallion"],
            contradiction_action_flags: ["action:state_contradiction_N3_N4"],
            contradiction_requirement_satisfied: true,
        };
        store.applySnapshot(snapshot);

        const inspect = mountInspectPanel(store, {
            presentationProfile: "demo",
            canDispatchInvestigationAction: () => true,
            dispatchInvestigationAction: async () => ({
                status: "accepted",
                code: "projection_affordance_observed",
                summary: "Action confirmed. Review new clues and keep following leads.",
                revealed_fact_ids: ["N7"],
                revealed_evidence_ids: [],
            }),
        });
        inspect.setSelection({ kind: "object", id: 3002 });

        const dialogue = mountDialoguePanel(store, {
            presentationProfile: "demo",
            canDispatchDialogueTurn: () => true,
            dispatchDialogueTurn: async () => ({
                status: "accepted",
                code: "ok",
                summary: "Line accepted",
                revealed_fact_ids: [],
            }),
        });
        dialogue.setInspectSelection({ kind: "room", id: 1 });

        const notebook = mountNotebookPanel(store, {
            presentationProfile: "demo",
        });
        const resolution = mountResolutionPanel(store, {
            presentationProfile: "demo",
            canDispatchResolutionAttempt: () => true,
        });

        document.body.appendChild(inspect.root);
        document.body.appendChild(dialogue.root);
        document.body.appendChild(notebook.root);
        document.body.appendChild(resolution.root);

        const inspectPanel = inspect.root.querySelector(".inspect-panel");
        expect(inspectPanel?.textContent).toContain(tr("inspect.section.field_prompt"));
        const inspectButtons = inspect.root.querySelectorAll<HTMLButtonElement>(".inspect-action-btn");
        expect(inspectButtons.length).toBeGreaterThan(0);
        expect(inspectButtons[0]?.disabled).toBe(false);
        inspectButtons[0]?.click();
        await flushUi();
        expect(inspectPanel?.textContent).toContain(tr("inspect.section.latest_result"));
        expect(inspectPanel?.textContent).not.toContain("Code");

        const dialoguePanel = dialogue.root.querySelector(".dialogue-panel");
        expect(dialoguePanel?.textContent).toContain(tr("dialogue.section.case_setup_hint"));
        expect(dialoguePanel?.textContent).toContain(tr("dialogue.section.choose_line"));
        expect(dialoguePanel?.textContent).not.toContain(tr("dialogue.section.summary_guidance"));
        expect(dialoguePanel?.textContent).toContain(tr("notebook.scene.S1"));
        expect(dialoguePanel?.textContent).toContain(tr("dialogue.line.who_to_question"));
        expect(dialoguePanel?.textContent).toContain(tr("dialogue.npc.elodie"));
        expect(dialoguePanel?.textContent).not.toContain("S1");
        const submitBtn = dialogue.root.querySelector<HTMLButtonElement>(".dialogue-submit");
        expect(submitBtn?.disabled).toBe(false);

        const notebookPanel = notebook.root.querySelector(".notebook-panel");
        expect(notebookPanel?.textContent).toContain(tr("notebook.section.case_setup"));
        expect(notebookPanel?.textContent).toContain(tr("notebook.setup.default_demo_route"));
        expect(notebookPanel?.textContent).not.toContain(tr("mbam.playtest.title"));
        expect(notebookPanel?.textContent).not.toContain(tr("notebook.line.truth_epoch"));
        expect(notebookPanel?.textContent).not.toContain("N1  ");
        expect(notebookPanel?.textContent).not.toContain("E2 ");

        const resolutionPanel = resolution.root.querySelector(".resolution-panel");
        expect(resolutionPanel?.textContent).toContain(tr("resolution.title.case_outcome"));
        expect(resolutionPanel?.textContent).toContain(tr("resolution.section.what_you_proved"));
        expect(resolutionPanel?.textContent).toContain(tr("resolution.section.what_mattered"));
        expect(resolutionPanel?.textContent).not.toContain(tr("resolution.line.resolution_path"));
    });

    it("evaluates MG1-MG4 notebook widgets deterministically", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(4));

        const notebook = mountNotebookPanel(store);
        document.body.appendChild(notebook.root);
        const panel = notebook.root.querySelector(".notebook-panel");
        const cards = Array.from(notebook.root.querySelectorAll<HTMLElement>(".notebook-minigame"));

        const mg1 = cards.find((card) => card.textContent?.includes(tr("notebook.mg1.title")));
        const mg2 = cards.find((card) => card.textContent?.includes(tr("notebook.mg2.title")));
        const mg3 = cards.find((card) => card.textContent?.includes(tr("notebook.mg3.title")));
        const mg4 = cards.find((card) => card.textContent?.includes(tr("notebook.mg4.title")));
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

        expect(panel?.textContent).toContain(tr("notebook.feedback.correct_score", { score: 2, max: 2 }));
        expect(panel?.textContent).toContain(tr("notebook.feedback.correct_score", { score: 3, max: 3 }));
    });

    it("updates internal playtest path milestones as live state progresses", () => {
        const store = new WorldStore();
        const initial = makeMbamSnapshot(40);
        if (!initial.state.investigation || !initial.state.dialogue || !initial.state.case_outcome || !initial.state.case_recap) {
            throw new Error("fixture must include required projections");
        }
        initial.state.investigation.objects = initial.state.investigation.objects.map((row) =>
            row.object_id === "O1_DISPLAY_CASE" ? { ...row, observed_affordances: [] } : row
        );
        initial.state.dialogue.recent_turns = [];
        initial.state.dialogue.learning = {
            ...initial.state.dialogue.learning!,
            minigames: initial.state.dialogue.learning!.minigames.map((row) => ({
                ...row,
                completed: false,
            })),
        };
        initial.state.investigation.contradictions.requirement_satisfied = false;
        initial.state.case_outcome.primary_outcome = "in_progress";
        initial.state.case_outcome.terminal = false;
        initial.state.case_recap.available = false;
        initial.state.case_recap.resolution_path = "in_progress";
        store.applySnapshot(initial);

        const notebook = mountNotebookPanel(store);
        document.body.appendChild(notebook.root);
        const panel = notebook.root.querySelector(".notebook-panel");
        expect(panel?.textContent).toContain(tr("mbam.playtest.title"));
        expect(panel?.textContent).toContain(
            tr("mbam.playtest.current.next", { label: tr("mbam.playtest.step.starter_investigation") })
        );

        const progressed = makeMbamSnapshot(41);
        if (!progressed.state.investigation || !progressed.state.dialogue || !progressed.state.case_outcome || !progressed.state.case_recap) {
            throw new Error("fixture must include required projections");
        }
        progressed.state.investigation.objects = progressed.state.investigation.objects.map((row) => {
            if (row.object_id === "O1_DISPLAY_CASE") {
                return { ...row, observed_affordances: ["inspect"] };
            }
            if (row.object_id === "O3_WALL_LABEL") {
                return { ...row, observed_affordances: ["read"] };
            }
            return row;
        });
        progressed.state.dialogue.recent_turns = [
            {
                turn_index: 3,
                scene_id: "S3",
                npc_id: "samira",
                intent_id: "challenge_contradiction",
                status: "accepted",
                code: "ok",
                outcome: "progressed",
                response_mode: "direct",
                revealed_fact_ids: ["N8"],
                trust_delta: 0,
                stress_delta: 0,
                repair_response_mode: null,
                summary_check_code: null,
            },
        ];
        progressed.state.dialogue.learning = {
            ...progressed.state.dialogue.learning!,
            minigames: progressed.state.dialogue.learning!.minigames.map((row, index) => ({
                ...row,
                completed: index === 0,
            })),
        };
        progressed.state.investigation.contradictions.requirement_satisfied = true;
        progressed.state.case_outcome.primary_outcome = "recovery_success";
        progressed.state.case_outcome.terminal = true;
        progressed.state.case_recap.available = true;
        progressed.state.case_recap.resolution_path = "recovery";

        store.applySnapshot(progressed);
        expect(panel?.textContent).toContain(tr("mbam.playtest.current.complete"));
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
        expect(panel?.textContent).toContain(tr("dialogue.line.difficulty"));
        expect(panel?.textContent).toContain("D1");
        expect(panel?.textContent).toContain(tr("dialogue.line.french_required"));
        expect(panel?.textContent).toContain(tr("dialogue.value.yes"));
        expect(panel?.textContent).toContain(tr("dialogue.line.english_help"));
        expect(panel?.textContent).toContain(tr("dialogue.value.off"));
        expect(panel?.textContent).toContain(`${tr("dialogue.hint_level.english_meta_help")} - ${tr("dialogue.hint_state.locked")}`);
        expect(panel?.textContent).toContain(tr("dialogue.hint.choose_one", { options: "" }).trim());
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
        const mg1Card = cards.find((card) => card.textContent?.includes(tr("notebook.mg1.title")));
        const mg2Card = cards.find((card) => card.textContent?.includes(tr("notebook.mg2.title")));
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
        expect(panel?.textContent).toContain(tr("notebook.feedback.incorrect_retry"));
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
        const mg1Card = cards.find((card) => card.textContent?.includes(tr("notebook.mg1.title")));
        expect(mg1Card).toBeTruthy();

        const mg1Inputs = Array.from(mg1Card!.querySelectorAll<HTMLInputElement>("input.notebook-minigame-input"));
        mg1Inputs[0]!.value = "Le Medaillon des Voyageurs";
        mg1Inputs[0]!.dispatchEvent(new Event("input"));
        mg1Inputs[1]!.value = "1898";
        mg1Inputs[1]!.dispatchEvent(new Event("input"));
        mg1Card!.querySelectorAll<HTMLButtonElement>(".notebook-minigame-btn")[0]!.click();
        await flushUi();

        expect(panel?.textContent).toContain(tr("notebook.minigame.connection_not_ready"));
        expect(panel?.textContent).not.toContain(tr("notebook.feedback.correct_score", { score: 2, max: 2 }));
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

        expect(panel?.textContent).toContain(tr("resolution.title.final_decision"));
        expect(panel?.textContent).toContain("best_outcome");
        expect(panel?.textContent).toContain("recovery");
        expect(panel?.textContent).toContain(tr("resolution.value.resolved"));
        expect(panel?.textContent).toContain(`${tr("resolution.fact.N3")} (N3)`);
        expect(panel?.textContent).toContain(`${tr("resolution.evidence.E2_CAFE_RECEIPT")} (E2_CAFE_RECEIPT)`);
        expect(panel?.textContent).toContain(tr("resolution.section.best_markers"));
        expect(panel?.textContent).toContain("quiet_recovery");
    });
});
