import { describe, expect, it } from "vitest";

import type { KvpClient } from "../kvp/client";
import { createFrontendActionBridge } from "../app/actionBridge";
import { WorldStore } from "../state/worldStore";
import { cloneDialogue, cloneInvestigation, makeMbamSnapshot, makeStateDiff } from "./mbamFixtures";

describe("Phase 5 action bridge", () => {
    it("returns unavailable while offline/replay", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(1));

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "offline",
            getClient: () => null,
            projectionTimeoutMs: 40,
        });

        const investigation = await bridge.submitInvestigationAction({
            worldObjectId: 3002,
            caseObjectId: "O1_DISPLAY_CASE",
            affordanceId: "inspect",
            tick: 1,
        });
        const dialogue = await bridge.submitDialogueTurn({
            sceneId: "S1",
            npcId: "elodie",
            intentId: "ask_what_happened",
            providedSlots: [],
            presentedFactIds: [],
            presentedEvidenceIds: [],
            tick: 1,
        });

        expect(bridge.canSubmitInvestigationAction()).toBe(false);
        expect(bridge.canSubmitDialogueTurn()).toBe(false);
        expect(investigation.status).toBe("unavailable");
        expect(dialogue.status).toBe("unavailable");
    });

    it("submits investigation command in live mode and resolves from projected state", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(2));

        const fakeClient = {
            canSendSimInput: () => true,
            sendSimInput: () => {
                const state = store.getState();
                const next = cloneInvestigation(state.investigation!);
                const displayCase = next.objects.find((row) => row.object_id === "O1_DISPLAY_CASE");
                if (displayCase) {
                    displayCase.observed_affordances = ["inspect"];
                    displayCase.known_state = { locked: true };
                }
                next.facts.known_fact_ids.push("N7");
                next.evidence.discovered_ids.push("E3_METHOD_TRACE");
                store.applyDiff(makeStateDiff(state, [{ op: "SET_INVESTIGATION", investigation: next }]));
                return true;
            },
        } as unknown as KvpClient;

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "live",
            getClient: () => fakeClient,
            projectionTimeoutMs: 40,
        });

        const result = await bridge.submitInvestigationAction({
            worldObjectId: 3002,
            caseObjectId: "O1_DISPLAY_CASE",
            affordanceId: "inspect",
            tick: 2,
        });

        expect(bridge.canSubmitInvestigationAction()).toBe(true);
        expect(result.status).toBe("accepted");
        expect(result.code).toBe("projection_affordance_observed");
        expect(result.revealed_fact_ids).toContain("N7");
        expect(result.revealed_evidence_ids).toContain("E3_METHOD_TRACE");
    });

    it("treats observed-not-collected evidence projection as investigation state change", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(2));

        const fakeClient = {
            canSendSimInput: () => true,
            sendSimInput: () => {
                const state = store.getState();
                const next = cloneInvestigation(state.investigation!);
                next.evidence.observed_not_collected_ids.push("clue:evidence:E3_METHOD_TRACE:observed_not_collected");
                store.applyDiff(makeStateDiff(state, [{ op: "SET_INVESTIGATION", investigation: next }]));
                return true;
            },
        } as unknown as KvpClient;

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "live",
            getClient: () => fakeClient,
            projectionTimeoutMs: 40,
        });

        const result = await bridge.submitInvestigationAction({
            worldObjectId: 3007,
            caseObjectId: "O9_RECEIPT_PRINTER",
            affordanceId: "ask_for_receipt",
            tick: 2,
        });

        expect(result.status).toBe("accepted");
        expect(result.code).toBe("projection_state_changed");
    });

    it("submits dialogue turn in live mode and maps projected turn status", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(3));

        const fakeClient = {
            canSendSimInput: () => true,
            sendSimInput: () => {
                const state = store.getState();
                const next = cloneDialogue(state.dialogue!);
                next.recent_turns.push({
                    turn_index: 1,
                    scene_id: "S1",
                    npc_id: "elodie",
                    intent_id: "summarize_understanding",
                    status: "repair",
                    code: "summary_missing_fact",
                    outcome: "summary_needs_more_facts",
                    response_mode: "sentence_stem",
                    revealed_fact_ids: [],
                    trust_delta: 0,
                    stress_delta: 0,
                    repair_response_mode: "sentence_stem",
                    summary_check_code: "insufficient_facts",
                });
                store.applyDiff(makeStateDiff(state, [{ op: "SET_DIALOGUE", dialogue: next }]));
                return true;
            },
        } as unknown as KvpClient;

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "live",
            getClient: () => fakeClient,
            projectionTimeoutMs: 40,
        });

        const result = await bridge.submitDialogueTurn({
            sceneId: "S1",
            npcId: "elodie",
            intentId: "summarize_understanding",
            providedSlots: [{ slot_name: "time", value: "18h05" }],
            presentedFactIds: ["N1"],
            presentedEvidenceIds: [],
            tick: 3,
        });

        expect(bridge.canSubmitDialogueTurn()).toBe(true);
        expect(result.status).toBe("repair");
        expect(result.code).toBe("summary_missing_fact");
        expect(result.summary).toContain("sentence_stem");
    });

    it("does not bind dialogue result to unrelated projected turns", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(4));

        const fakeClient = {
            canSendSimInput: () => true,
            sendSimInput: () => {
                const state = store.getState();
                const next = cloneDialogue(state.dialogue!);
                next.recent_turns.push({
                    turn_index: 1,
                    scene_id: "S2",
                    npc_id: "marc",
                    intent_id: "request_access",
                    status: "accepted",
                    code: "ok",
                    outcome: "access_path_shared",
                    response_mode: "direct",
                    revealed_fact_ids: ["N2"],
                    trust_delta: 0,
                    stress_delta: 0,
                    repair_response_mode: null,
                    summary_check_code: null,
                });
                store.applyDiff(makeStateDiff(state, [{ op: "SET_DIALOGUE", dialogue: next }]));
                return true;
            },
        } as unknown as KvpClient;

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "live",
            getClient: () => fakeClient,
            projectionTimeoutMs: 30,
        });

        const result = await bridge.submitDialogueTurn({
            sceneId: "S1",
            npcId: "elodie",
            intentId: "summarize_understanding",
            providedSlots: [],
            presentedFactIds: ["N1"],
            presentedEvidenceIds: [],
            tick: 4,
        });

        expect(result.status).toBe("submitted");
        expect(result.code).toBe("awaiting_projection_update");
    });
});
