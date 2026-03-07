import { describe, expect, it } from "vitest";

import { WorldStore } from "../state/worldStore";
import { cloneDialogue, cloneInvestigation, makeMbamSnapshot, makeStateDiff } from "./mbamFixtures";

describe("WorldStore Phase 5 shell ingestion", () => {
    it("ingests case/npc/investigation/dialogue fields from snapshot deterministically", () => {
        const store = new WorldStore();
        const snapshot = makeMbamSnapshot(10);
        store.applySnapshot(snapshot);

        const state = store.getState();
        expect(state.tick).toBe(10);
        expect(state.caseState?.case_id).toBe("MBAM_01");
        expect(state.caseState?.seed).toBe("A");
        expect(state.npcSemantic).toHaveLength(2);
        expect(state.npcSemantic[0]?.npc_id).toBe("elodie");
        expect(state.investigation?.objects[0]?.object_id).toBe("O1_DISPLAY_CASE");
        expect(state.dialogue?.active_scene_id).toBe("S1");
    });

    it("clones nested projected structures instead of aliasing snapshot payload objects", () => {
        const store = new WorldStore();
        const snapshot = makeMbamSnapshot(11);
        store.applySnapshot(snapshot);

        snapshot.state.case?.visible_case_slice.public_room_ids.push("LEAK");
        snapshot.state.npc_semantic?.[0]?.visible_behavior_flags.push("leak_flag");
        snapshot.state.investigation?.facts.known_fact_ids.push("LEAK");
        snapshot.state.dialogue?.recent_turns[0]?.revealed_fact_ids.push("LEAK");

        const state = store.getState();
        expect(state.caseState?.visible_case_slice.public_room_ids).not.toContain("LEAK");
        expect(state.npcSemantic[0]?.visible_behavior_flags).not.toContain("leak_flag");
        expect(state.investigation?.facts.known_fact_ids).not.toContain("LEAK");
        expect(state.dialogue?.recent_turns[0]?.revealed_fact_ids).not.toContain("LEAK");
    });

    it("applies SET_INVESTIGATION and SET_DIALOGUE diffs coherently", () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(20));
        const base = store.getState();
        const investigation = cloneInvestigation(base.investigation!);
        const dialogue = cloneDialogue(base.dialogue!);

        investigation.facts.known_fact_ids.push("N3");
        dialogue.revealed_fact_ids.push("N3");
        dialogue.recent_turns.push({
            turn_index: 1,
            scene_id: "S1",
            npc_id: "elodie",
            intent_id: "summarize_understanding",
            status: "accepted",
            code: "summary_ok",
            outcome: "summary_accepted",
            response_mode: "direct",
            revealed_fact_ids: ["N3"],
            trust_delta: 1,
            stress_delta: 0,
            repair_response_mode: null,
            summary_check_code: "ok",
        });

        store.applyDiff(
            makeStateDiff(base, [
                { op: "SET_INVESTIGATION", investigation },
                { op: "SET_DIALOGUE", dialogue },
            ])
        );

        const after = store.getState();
        expect(after.tick).toBe(21);
        expect(after.investigation?.facts.known_fact_ids).toContain("N3");
        expect(after.dialogue?.revealed_fact_ids).toContain("N3");
        expect(after.dialogue?.recent_turns.at(-1)?.code).toBe("summary_ok");
    });
});
