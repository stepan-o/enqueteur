import { afterEach, describe, expect, it } from "vitest";

import { mountResolutionPanel } from "../ui/resolutionPanel";
import { WorldStore } from "../state/worldStore";
import { makeMbamSnapshot } from "./mbamFixtures";

afterEach(() => {
    document.body.innerHTML = "";
});

describe("Phase 7 terminal path resolution panel smoke", () => {
    it("renders recovery, accusation, and soft-fail terminal outcomes deterministically", () => {
        const cases: Array<{
            outcome: "recovery_success" | "accusation_success" | "soft_fail";
            path: "recovery" | "accusation" | "soft_fail";
        }> = [
            { outcome: "recovery_success", path: "recovery" },
            { outcome: "accusation_success", path: "accusation" },
            { outcome: "soft_fail", path: "soft_fail" },
        ];

        for (const scenario of cases) {
            const store = new WorldStore();
            const snapshot = makeMbamSnapshot(20);
            if (!snapshot.state.case_outcome || !snapshot.state.case_recap) {
                throw new Error("fixture must include case outcome + recap projections");
            }
            snapshot.state.case_outcome = {
                ...snapshot.state.case_outcome,
                primary_outcome: scenario.outcome,
                terminal: true,
                recovery_success: scenario.outcome === "recovery_success",
                accusation_success: scenario.outcome === "accusation_success",
                soft_fail: scenario.outcome === "soft_fail",
            };
            snapshot.state.case_recap = {
                ...snapshot.state.case_recap,
                available: true,
                final_outcome_type: scenario.outcome,
                resolution_path: scenario.path,
            };
            store.applySnapshot(snapshot);

            const panelHandle = mountResolutionPanel(store);
            document.body.appendChild(panelHandle.root);
            const text = panelHandle.root.textContent ?? "";
            expect(text).toContain("Decision Board");
            expect(text).toContain(scenario.outcome);
            expect(text).toContain(scenario.path);
            panelHandle.root.remove();
        }
    });
});
