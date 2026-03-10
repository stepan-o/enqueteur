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
            expect(text).toContain("Final Decision");
            expect(text).toContain("Decision Readiness");
            expect(text).toContain("Why This Ending");
            expect(text).toContain(scenario.outcome);
            expect(text).toContain(scenario.path);
            panelHandle.root.remove();
        }
    });

    it("surfaces accusation prereq blocking before terminal recap", () => {
        const store = new WorldStore();
        const snapshot = makeMbamSnapshot(21);
        store.applySnapshot(snapshot);

        const panelHandle = mountResolutionPanel(store, {
            canDispatchResolutionAttempt: () => true,
            dispatchAttemptRecovery: async () => ({
                status: "submitted",
                code: "command_accepted_waiting_projection",
                summary: "Recovery accepted",
            }),
            dispatchAttemptAccusation: async () => ({
                status: "blocked",
                code: "ACCUSATION_PREREQS_MISSING",
                summary: "Missing prerequisites",
            }),
        });
        document.body.appendChild(panelHandle.root);
        const text = panelHandle.root.textContent ?? "";
        expect(text).toContain("Decision Readiness");
        expect(text).toContain("Recoveryavailable - your corroboration is strong enough to proceed");
        expect(text).toContain("Accusationblocked - you still need contradiction support before accusing");
        panelHandle.root.remove();
    });

    it("renders external-demo-friendly recap language without debug-style outcome codes", () => {
        const store = new WorldStore();
        const snapshot = makeMbamSnapshot(22);
        if (!snapshot.state.case_outcome || !snapshot.state.case_recap) {
            throw new Error("fixture must include case outcome + recap projections");
        }
        snapshot.state.case_outcome = {
            ...snapshot.state.case_outcome,
            primary_outcome: "recovery_success",
            terminal: true,
            recovery_success: true,
            accusation_success: false,
            soft_fail: false,
        };
        snapshot.state.case_recap = {
            ...snapshot.state.case_recap,
            available: true,
            final_outcome_type: "recovery_success",
            resolution_path: "recovery",
            key_fact_ids: ["N1", "N3", "N4"],
            key_evidence_ids: ["E2_CAFE_RECEIPT"],
            key_action_flags: ["action:recover_medallion"],
            contradiction_action_flags: ["action:state_contradiction_N3_N4"],
        };
        store.applySnapshot(snapshot);

        const panelHandle = mountResolutionPanel(store, {
            presentationProfile: "demo",
        });
        document.body.appendChild(panelHandle.root);
        const text = panelHandle.root.textContent ?? "";
        expect(text).toContain("Case Outcome");
        expect(text).toContain("Recovery Success");
        expect(text).toContain("What You Proved");
        expect(text).toContain("What Mattered Most");
        expect(text).not.toContain("Resolution path");
        panelHandle.root.remove();
    });
});
