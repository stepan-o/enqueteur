import { describe, expect, it } from "vitest";

import { createFrontendActionBridge } from "../app/actionBridge";
import type { LiveCommandBridge } from "../app/live/liveCommandBridge";
import { setLocale } from "../i18n";
import { WorldStore } from "../state/worldStore";
import { cloneDialogue, cloneInvestigation, makeMbamSnapshot, makeStateDiff } from "./mbamFixtures";

function makeLiveCommandBridge(args: {
    canSend?: boolean;
    onSend: (params: { cmd: { type: string; payload: Record<string, unknown> }; opts?: { tickTarget?: number } }) => void;
}): LiveCommandBridge {
    const { canSend = true, onSend } = args;
    return {
        canSendInputCommand: () => canSend,
        sendInputCommand: async (cmd, opts) => {
            onSend({ cmd, opts });
            return {
                accepted: true,
                clientCmdId: "00000000-0000-4000-8000-000000000001",
            };
        },
    };
}

describe("Phase 5 action bridge", () => {
    it("returns unavailable while offline/replay", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(1));

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "offline",
            getLiveCommandBridge: () => null,
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

        const liveCommandBridge = makeLiveCommandBridge({
            onSend: () => {
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
            },
        });

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "live",
            getLiveCommandBridge: () => liveCommandBridge,
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

        const liveCommandBridge = makeLiveCommandBridge({
            onSend: () => {
                const state = store.getState();
                const next = cloneInvestigation(state.investigation!);
                next.evidence.observed_not_collected_ids.push("clue:evidence:E3_METHOD_TRACE:observed_not_collected");
                store.applyDiff(makeStateDiff(state, [{ op: "SET_INVESTIGATION", investigation: next }]));
            },
        });

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "live",
            getLiveCommandBridge: () => liveCommandBridge,
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

        const liveCommandBridge = makeLiveCommandBridge({
            onSend: () => {
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
            },
        });

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "live",
            getLiveCommandBridge: () => liveCommandBridge,
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

        const liveCommandBridge = makeLiveCommandBridge({
            onSend: () => {
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
            },
        });

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "live",
            getLiveCommandBridge: () => liveCommandBridge,
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

    it("maps shell action requests to Enqueteur live INPUT_COMMAND payload shapes", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(5));
        const sent: Array<{ cmd: { type: string; payload: Record<string, unknown> }; opts?: { tickTarget?: number } }> = [];

        const liveCommandBridge = makeLiveCommandBridge({
            onSend: ({ cmd, opts }) => {
                sent.push({ cmd, opts });
            },
        });

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "live",
            getLiveCommandBridge: () => liveCommandBridge,
            projectionTimeoutMs: 30,
        });

        await bridge.submitInvestigationAction({
            worldObjectId: 3002,
            caseObjectId: "O1_DISPLAY_CASE",
            affordanceId: "inspect",
            tick: 5,
        });
        await bridge.submitDialogueTurn({
            sceneId: "S2",
            npcId: "marc",
            intentId: "request_access",
            providedSlots: [{ slot_name: "reason", value: "verify timeline" }],
            presentedFactIds: ["N3"],
            presentedEvidenceIds: ["E2_CAFE_RECEIPT"],
            tick: 5,
        });
        await bridge.submitMinigameSubmit({
            minigameId: "MG2",
            targetId: "O6_BADGE_TERMINAL",
            answer: { selected_entry_id: "entry_3", time_value: "17:58" },
            tick: 5,
        });
        await bridge.submitAttemptRecovery({
            targetId: "O2_MEDALLION",
            tick: 5,
        });
        await bridge.submitAttemptAccusation({
            suspectId: "samira",
            supportingFactIds: ["N3", "N4"],
            supportingEvidenceIds: ["E2_CAFE_RECEIPT"],
            tick: 5,
        });

        expect(sent).toHaveLength(5);
        expect(sent[0]).toMatchObject({
            cmd: {
                type: "INVESTIGATE_OBJECT",
                payload: {
                    object_id: "O1_DISPLAY_CASE",
                    action_id: "inspect",
                },
            },
            opts: { tickTarget: 6 },
        });
        expect(sent[1]).toMatchObject({
            cmd: {
                type: "DIALOGUE_TURN",
                payload: {
                    scene_id: "S2",
                    npc_id: "marc",
                    intent_id: "request_access",
                    slots: { reason: "verify timeline" },
                },
            },
            opts: { tickTarget: 6 },
        });
        expect(sent[2]).toMatchObject({
            cmd: {
                type: "MINIGAME_SUBMIT",
                payload: {
                    minigame_id: "MG2",
                    target_id: "O6_BADGE_TERMINAL",
                    answer: { selected_entry_id: "entry_3", time_value: "17:58" },
                },
            },
            opts: { tickTarget: 6 },
        });
        expect(sent[3]).toMatchObject({
            cmd: {
                type: "ATTEMPT_RECOVERY",
                payload: { target_id: "O2_MEDALLION" },
            },
            opts: { tickTarget: 6 },
        });
        expect(sent[4]).toMatchObject({
            cmd: {
                type: "ATTEMPT_ACCUSATION",
                payload: {
                    suspect_id: "samira",
                    supporting_fact_ids: ["N3", "N4"],
                    supporting_evidence_ids: ["E2_CAFE_RECEIPT"],
                },
            },
            opts: { tickTarget: 6 },
        });
    });

    it("maps COMMAND_REJECTED to coherent non-optimistic action statuses", async () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(6));

        const liveCommandBridge: LiveCommandBridge = {
            canSendInputCommand: () => true,
            sendInputCommand: async (cmd) => {
                if (cmd.type === "MINIGAME_SUBMIT") {
                    return {
                        accepted: false,
                        clientCmdId: "00000000-0000-4000-8000-000000000002",
                        reasonCode: "MINIGAME_INVALID_STATE",
                        message: "Minigame is not open.",
                    };
                }
                return {
                    accepted: false,
                    clientCmdId: "00000000-0000-4000-8000-000000000003",
                    reasonCode: "INVALID_COMMAND",
                    message: "Payload shape invalid.",
                };
            },
        };

        const bridge = createFrontendActionBridge({
            store,
            getMode: () => "live",
            getLiveCommandBridge: () => liveCommandBridge,
            projectionTimeoutMs: 30,
        });

        const minigame = await bridge.submitMinigameSubmit({
            minigameId: "MG2",
            targetId: "O6_BADGE_TERMINAL",
            answer: { selected_entry_id: "entry_3", time_value: "17:58" },
            tick: 6,
        });
        const accusation = await bridge.submitAttemptAccusation({
            suspectId: "samira",
            supportingFactIds: ["N3", "N4"],
            supportingEvidenceIds: ["E2_CAFE_RECEIPT"],
            tick: 6,
        });

        expect(minigame.status).toBe("blocked");
        expect(minigame.code).toBe("MINIGAME_INVALID_STATE");
        expect(minigame.summary).toBe("Minigame is not open.");

        expect(accusation.status).toBe("invalid");
        expect(accusation.code).toBe("INVALID_COMMAND");
        expect(accusation.summary).toBe("Payload shape invalid.");
    });

    it("prefers localized message_key rendering for command rejection summaries", async () => {
        setLocale("fr");
        try {
            const store = new WorldStore();
            store.applySnapshot(makeMbamSnapshot(7));

            const liveCommandBridge: LiveCommandBridge = {
                canSendInputCommand: () => true,
                sendInputCommand: async () => ({
                    accepted: false,
                    clientCmdId: "00000000-0000-4000-8000-000000000004",
                    reasonCode: "INVALID_COMMAND",
                    message: "Payload shape invalid.",
                    messageKey: "live.command_rejected.invalid_command",
                    messageParams: { reason_code: "INVALID_COMMAND" },
                }),
            };

            const bridge = createFrontendActionBridge({
                store,
                getMode: () => "live",
                getLiveCommandBridge: () => liveCommandBridge,
                projectionTimeoutMs: 30,
            });

            const result = await bridge.submitAttemptRecovery({
                targetId: "O2_MEDALLION",
                tick: 7,
            });

            expect(result.status).toBe("invalid");
            expect(result.summary).toBe("Le format de cette action est invalide. Rouvrez le panneau puis reessayez.");
        } finally {
            setLocale("en");
        }
    });
});
