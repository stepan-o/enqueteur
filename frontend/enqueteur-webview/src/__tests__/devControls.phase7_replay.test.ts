import { afterEach, describe, expect, it } from "vitest";

import { mountDevControls } from "../ui/devControls";
import { WorldStore } from "../state/worldStore";
import { makeMbamSnapshot, makeStateDiff } from "./mbamFixtures";

afterEach(() => {
    document.body.innerHTML = "";
});

describe("Phase 7 replay run panel", () => {
    it("renders seed, outcome, recap, and progression milestones from projected state", () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(8));

        const controls = mountDevControls({
            store,
            onFloorChange: () => {},
            onRestart: () => {},
        });
        document.body.appendChild(controls);

        const text = controls.textContent ?? "";
        expect(text).toContain("Replay Run");
        expect(text).toContain("Seed");
        expect(text).toContain("A");
        expect(text).toContain("Outcome");
        expect(text).toContain("in_progress");
        expect(text).toContain("Recap");
        expect(text).toContain("pending");
        expect(text).toContain("Milestones: scenes 0/5 | facts 4 | evidence 0/2 | contradiction pending | summaries 0");
    });

    it("updates replay summary when terminal outcome and recap projection arrive", () => {
        const store = new WorldStore();
        store.applySnapshot(makeMbamSnapshot(9));

        const controls = mountDevControls({
            store,
            onFloorChange: () => {},
            onRestart: () => {},
        });
        document.body.appendChild(controls);

        const state = store.getState();
        const nextOutcome = {
            ...state.caseOutcome!,
            primary_outcome: "best_outcome",
            terminal: true,
            best_outcome: true,
            best_outcome_awarded: true,
        };
        const nextRecap = {
            ...state.caseRecap!,
            available: true,
            final_outcome_type: "best_outcome",
            resolution_path: "recovery",
        };

        store.applyDiff(
            makeStateDiff(state, [
                { op: "SET_CASE_OUTCOME", case_outcome: nextOutcome },
                { op: "SET_CASE_RECAP", case_recap: nextRecap },
            ])
        );

        const text = controls.textContent ?? "";
        expect(text).toContain("best_outcome");
        expect(text).toContain("best_outcome (recovery)");
    });
});
