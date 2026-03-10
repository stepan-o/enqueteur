import { describe, expect, it } from "vitest";

import { makeMbamSnapshot } from "./mbamFixtures";
import { buildMbamPlaytestPathView } from "../ui/mbamOnboarding";
import type { WorldState } from "../state/worldStore";

function toWorldStateFromSnapshot(snapshot: ReturnType<typeof makeMbamSnapshot>): WorldState {
    const investigation = snapshot.state.investigation;
    const dialogue = snapshot.state.dialogue;
    const caseOutcome = snapshot.state.case_outcome;
    const caseRecap = snapshot.state.case_recap;

    if (!investigation || !dialogue || !caseOutcome || !caseRecap) {
        throw new Error("fixture must include investigation/dialogue/outcome/recap projections");
    }

    return {
        mode: "live",
        tick: snapshot.tick,
        stepHash: snapshot.step_hash,
        connected: true,
        desynced: false,
        world: snapshot.state.world ?? null,
        rooms: new Map((snapshot.state.rooms ?? []).map((room) => [room.room_id, room])),
        agents: new Map((snapshot.state.agents ?? []).map((agent) => [agent.agent_id, agent])),
        items: new Map((snapshot.state.items ?? []).map((item) => [item.item_id, item])),
        objects: new Map((snapshot.state.objects ?? []).map((objectRow) => [objectRow.object_id, objectRow])),
        events: new Map(),
        caseState: snapshot.state.case ?? null,
        npcSemantic: snapshot.state.npc_semantic ?? [],
        investigation,
        dialogue,
        caseOutcome,
        caseRecap,
    };
}

describe("Phase G5 internal playtest path tracker", () => {
    it("marks the first incomplete golden-path milestone during early run", () => {
        const snapshot = makeMbamSnapshot(30);
        if (!snapshot.state.investigation || !snapshot.state.dialogue || !snapshot.state.case_outcome || !snapshot.state.case_recap) {
            throw new Error("fixture must include required projections");
        }

        snapshot.state.investigation.objects = snapshot.state.investigation.objects.map((row) =>
            row.object_id === "O1_DISPLAY_CASE"
                ? { ...row, observed_affordances: [] }
                : row
        );
        snapshot.state.dialogue.recent_turns = [];
        snapshot.state.dialogue.learning = {
            ...snapshot.state.dialogue.learning!,
            minigames: snapshot.state.dialogue.learning!.minigames.map((row) => ({
                ...row,
                completed: false,
            })),
        };
        snapshot.state.investigation.contradictions.requirement_satisfied = false;
        snapshot.state.case_outcome.primary_outcome = "in_progress";
        snapshot.state.case_outcome.terminal = false;
        snapshot.state.case_recap.available = false;
        snapshot.state.case_recap.resolution_path = "in_progress";

        const view = buildMbamPlaytestPathView(toWorldStateFromSnapshot(snapshot));

        expect(view.title).toBe("Internal Playtest Path");
        expect(view.currentMilestone).toContain("Inspect starter objects");
        const doneCount = view.steps.filter((row) => row.done).length;
        expect(doneCount).toBe(0);
    });

    it("reports path complete when recap is available after terminal outcome", () => {
        const snapshot = makeMbamSnapshot(31);
        if (!snapshot.state.investigation || !snapshot.state.dialogue || !snapshot.state.case_outcome || !snapshot.state.case_recap) {
            throw new Error("fixture must include required projections");
        }

        snapshot.state.investigation.objects = snapshot.state.investigation.objects.map((row) => {
            if (row.object_id === "O1_DISPLAY_CASE") {
                return { ...row, observed_affordances: ["inspect"] };
            }
            if (row.object_id === "O3_WALL_LABEL") {
                return { ...row, observed_affordances: ["read"] };
            }
            return row;
        });
        snapshot.state.dialogue.recent_turns = [
            {
                turn_index: 2,
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
        snapshot.state.dialogue.learning = {
            ...snapshot.state.dialogue.learning!,
            minigames: snapshot.state.dialogue.learning!.minigames.map((row, index) => ({
                ...row,
                completed: index === 0,
            })),
        };
        snapshot.state.investigation.contradictions.requirement_satisfied = true;
        snapshot.state.case_outcome.primary_outcome = "recovery_success";
        snapshot.state.case_outcome.terminal = true;
        snapshot.state.case_recap.available = true;
        snapshot.state.case_recap.resolution_path = "recovery";

        const view = buildMbamPlaytestPathView(toWorldStateFromSnapshot(snapshot));

        expect(view.currentMilestone).toContain("Path complete");
        expect(view.steps.every((row) => row.done)).toBe(true);
    });
});
