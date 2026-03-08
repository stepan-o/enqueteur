import type { WorldState, WorldStore } from "../state/worldStore";

export type ResolutionPanelHandle = {
    root: HTMLElement;
};

const FACT_LABELS: Record<string, string> = {
    N1: "N1 Missing item discovered",
    N2: "N2 Corridor badge access",
    N3: "N3 Badge log 17h58",
    N4: "N4 Cafe receipt 17h52",
    N5: "N5 Witness clothing",
    N6: "N6 Torn note clue",
    N7: "N7 Vitrine latch clue",
    N8: "N8 Drop location clue",
};

const EVIDENCE_LABELS: Record<string, string> = {
    E1_TORN_NOTE: "E1 Torn Note",
    E2_CAFE_RECEIPT: "E2 Cafe Receipt",
    E3_METHOD_TRACE: "E3 Method Trace",
};

export function mountResolutionPanel(store: WorldStore): ResolutionPanelHandle {
    const root = document.createElement("div");
    root.className = "resolution-root";

    const panel = document.createElement("div");
    panel.className = "resolution-panel";
    root.appendChild(panel);

    let lastState: WorldState | null = null;

    const render = (): void => {
        panel.innerHTML = "";
        if (!lastState) {
            panel.style.display = "none";
            return;
        }
        panel.style.display = "block";

        const title = document.createElement("div");
        title.className = "resolution-title";
        title.textContent = "Case Resolution";
        panel.appendChild(title);

        const recap = lastState.caseRecap;
        const outcome = lastState.caseOutcome;
        if (!recap && !outcome) {
            renderInfo(panel, "Resolution summary is not available in this projection.");
            return;
        }

        const truthEpoch = recap?.truth_epoch ?? outcome?.truth_epoch ?? 1;
        const finalOutcome = recap?.final_outcome_type ?? outcome?.primary_outcome ?? "in_progress";
        const path = recap?.resolution_path ?? fallbackPathFromOutcome(outcome?.primary_outcome);
        const available = recap?.available ?? Boolean(outcome?.terminal);
        const contradictionUsed = recap?.contradiction_used ?? false;
        const contradictionSatisfied = recap?.contradiction_requirement_satisfied ?? (outcome?.contradiction_requirement_satisfied ?? false);
        const bestAwarded = recap?.best_outcome.awarded ?? (outcome?.best_outcome_awarded ?? false);

        renderLines(panel, [
            ["Truth epoch", String(truthEpoch)],
            ["Outcome", finalOutcome],
            ["Resolution path", path],
            ["Status", available ? "resolved" : "in progress"],
            ["Contradiction", contradictionUsed ? "used" : (contradictionSatisfied ? "satisfied" : "pending")],
            ["Best outcome", bestAwarded ? "awarded" : "not awarded"],
        ]);

        if (!recap) {
            return;
        }
        if (!recap.available) {
            renderInfo(panel, "Final recap unlocks when the run reaches a terminal outcome.");
            return;
        }

        renderSection(panel, "Key Facts", recap.key_fact_ids.map((factId) => FACT_LABELS[factId] ?? factId));
        renderSection(panel, "Key Evidence", recap.key_evidence_ids.map((evidenceId) => EVIDENCE_LABELS[evidenceId] ?? evidenceId));
        renderSection(panel, "Relationship Flags", recap.relationship_result_flags);
        renderSection(panel, "Continuity Flags", recap.continuity_flags);

        const markers: string[] = [];
        if (recap.best_outcome.awarded) markers.push("best_outcome_awarded");
        if (recap.best_outcome.quiet_recovery) markers.push("quiet_recovery");
        if (recap.best_outcome.no_public_escalation) markers.push("no_public_escalation");
        if (recap.best_outcome.strong_key_trust) markers.push("strong_key_trust");
        if (markers.length > 0) {
            renderSection(panel, "Best Outcome Markers", markers);
        }
        if (recap.soft_fail.triggered) {
            renderSection(panel, "Soft-Fail Triggers", recap.soft_fail.trigger_conditions);
        }
    };

    const unsub = store.subscribe((state) => {
        lastState = state;
        render();
    });
    root.addEventListener("DOMNodeRemoved", () => unsub(), { once: true });

    return { root };
}

function fallbackPathFromOutcome(outcome: string | undefined): string {
    if (outcome === "soft_fail") return "soft_fail";
    if (outcome === "recovery_success") return "recovery";
    if (outcome === "accusation_success") return "accusation";
    if (outcome === "best_outcome") return "recovery";
    return "in_progress";
}

function renderSection(panel: HTMLElement, title: string, rows: string[]): void {
    if (rows.length === 0) return;
    renderSectionTitle(panel, title);
    const list = document.createElement("div");
    list.className = "resolution-list";
    for (const rowText of rows) {
        const row = document.createElement("div");
        row.className = "resolution-row";
        row.textContent = rowText;
        list.appendChild(row);
    }
    panel.appendChild(list);
}

function renderSectionTitle(panel: HTMLElement, label: string): void {
    const title = document.createElement("div");
    title.className = "resolution-section-title";
    title.textContent = label;
    panel.appendChild(title);
}

function renderLines(panel: HTMLElement, rows: Array<[string, string]>): void {
    for (const [labelText, valueText] of rows) {
        const row = document.createElement("div");
        row.className = "resolution-line";

        const label = document.createElement("span");
        label.className = "resolution-label";
        label.textContent = labelText;
        row.appendChild(label);

        const value = document.createElement("span");
        value.className = "resolution-value";
        value.textContent = valueText;
        row.appendChild(value);

        panel.appendChild(row);
    }
}

function renderInfo(panel: HTMLElement, text: string): void {
    const line = document.createElement("div");
    line.className = "resolution-info";
    line.textContent = text;
    panel.appendChild(line);
}
