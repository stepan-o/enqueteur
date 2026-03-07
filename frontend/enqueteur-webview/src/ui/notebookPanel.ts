// src/ui/notebookPanel.ts
import type { KvpInvestigationState, WorldState, WorldStore } from "../state/worldStore";

export type NotebookPanelHandle = {
    root: HTMLElement;
};

const EVIDENCE_LABELS: Record<string, string> = {
    E1_TORN_NOTE: "E1 Torn Note",
    E2_CAFE_RECEIPT: "E2 Cafe Receipt",
    E3_METHOD_TRACE: "E3 Lanyard Fiber/Sticker",
};

const FACT_LABELS: Record<string, string> = {
    N1: "Missing item discovered (~18h05)",
    N2: "Staff badge required for corridor",
    N3: "Badge log entry (17h58)",
    N4: "Cafe receipt timestamp (17h52)",
    N5: "Witness clothing description",
    N6: "Torn note directional/time clue",
    N7: "Display case latch/lock clue",
    N8: "Drop location clue",
};

const FACT_TIMELINE_ORDER: string[] = ["N4", "N3", "N1", "N5", "N6", "N7", "N8", "N2"];

const OBJECT_LABELS: Record<string, string> = {
    O1_DISPLAY_CASE: "Display Case",
    O2_MEDALLION: "Medallion",
    O3_WALL_LABEL: "Wall Label",
    O4_BENCH: "Bench",
    O5_VISITOR_LOGBOOK: "Visitor Logbook",
    O6_BADGE_TERMINAL: "Badge Terminal",
    O7_SECURITY_BINDER: "Security Binder",
    O8_KEYPAD_DOOR: "Keypad Door",
    O9_RECEIPT_PRINTER: "Receipt Printer",
    O10_BULLETIN_BOARD: "Bulletin Board",
};

export function mountNotebookPanel(store: WorldStore): NotebookPanelHandle {
    const root = document.createElement("div");
    root.className = "notebook-root";

    const panel = document.createElement("div");
    panel.className = "notebook-panel";
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
        title.className = "notebook-title";
        title.textContent = "Notebook";
        panel.appendChild(title);

        const investigation = lastState.investigation;
        if (!investigation) {
            renderInfo(panel, "Investigation projection not available in current state.");
            return;
        }

        renderLines(panel, [
            ["Case", lastState.caseState?.case_id ?? "MBAM_01"],
            ["Seed", lastState.caseState?.seed ?? "-"],
            ["Truth epoch", String(investigation.truth_epoch)],
        ]);

        renderSectionTitle(panel, "Evidence Tray");
        renderEvidenceTray(panel, investigation);

        renderSectionTitle(panel, "Fact Visibility");
        renderFactVisibility(panel, investigation);

        renderSectionTitle(panel, "Contradictions");
        renderContradictions(panel, investigation);

        renderSectionTitle(panel, "Timeline Clues");
        renderTimeline(panel, investigation);
    };

    store.subscribe((state) => {
        lastState = state;
        render();
    });

    return { root };
}

function renderEvidenceTray(panel: HTMLElement, investigation: KvpInvestigationState): void {
    const collected = new Set(investigation.evidence.collected_ids);
    const discovered = investigation.evidence.discovered_ids;
    if (discovered.length === 0 && investigation.evidence.observed_not_collected_ids.length === 0) {
        renderInfo(panel, "No evidence discovered yet.");
        return;
    }

    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);

    for (const evidenceId of discovered) {
        const row = document.createElement("div");
        row.className = "notebook-row";
        row.textContent = `${labelForEvidence(evidenceId)}  ${collected.has(evidenceId) ? "[collected]" : "[discovered]"}`;
        list.appendChild(row);
    }

    const observedOnly = investigation.evidence.observed_not_collected_ids.map(extractEvidenceIdFromObservedClue).filter(Boolean) as string[];
    for (const evidenceId of observedOnly) {
        if (collected.has(evidenceId)) continue;
        const row = document.createElement("div");
        row.className = "notebook-row is-observed";
        row.textContent = `${labelForEvidence(evidenceId)}  [observed-not-collected]`;
        list.appendChild(row);
    }

    const relevantObjects = investigation.objects
        .filter((obj) => obj.observed_affordances.length > 0)
        .map((obj) => `${labelForObject(obj.object_id)} (${obj.observed_affordances.length} observed actions)`);
    if (relevantObjects.length > 0) {
        renderInfo(panel, `Relevant objects: ${relevantObjects.join(" | ")}`);
    }
}

function renderFactVisibility(panel: HTMLElement, investigation: KvpInvestigationState): void {
    const knownFacts = investigation.facts.known_fact_ids;
    if (knownFacts.length === 0) {
        renderInfo(panel, "No visible facts unlocked yet.");
        return;
    }
    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);
    for (const factId of knownFacts) {
        const row = document.createElement("div");
        row.className = "notebook-row";
        row.textContent = `${factId}  ${labelForFact(factId)}`;
        list.appendChild(row);
    }
}

function renderContradictions(panel: HTMLElement, investigation: KvpInvestigationState): void {
    const contradictions = investigation.contradictions;
    renderLines(panel, [
        ["Required for accusation", contradictions.required_for_accusation ? "yes" : "no"],
        ["Requirement satisfied", contradictions.requirement_satisfied ? "yes" : "no"],
        ["Unlockable edges", String(contradictions.unlockable_edge_ids.length)],
        ["Known edges", String(contradictions.known_edge_ids.length)],
    ]);

    if (contradictions.unlockable_edge_ids.length > 0) {
        const unlockable = document.createElement("div");
        unlockable.className = "notebook-mini";
        unlockable.textContent = `Unlockable: ${contradictions.unlockable_edge_ids.join(", ")}`;
        panel.appendChild(unlockable);
    }
    if (contradictions.known_edge_ids.length > 0) {
        const known = document.createElement("div");
        known.className = "notebook-mini";
        known.textContent = `Known: ${contradictions.known_edge_ids.join(", ")}`;
        panel.appendChild(known);
    }
}

function renderTimeline(panel: HTMLElement, investigation: KvpInvestigationState): void {
    const knownFactSet = new Set(investigation.facts.known_fact_ids);
    const ordered = FACT_TIMELINE_ORDER.filter((factId) => knownFactSet.has(factId));
    if (ordered.length === 0) {
        renderInfo(panel, "No timeline clues visible yet.");
        return;
    }
    const list = document.createElement("div");
    list.className = "notebook-list";
    panel.appendChild(list);
    for (const factId of ordered) {
        const row = document.createElement("div");
        row.className = "notebook-row is-timeline";
        row.textContent = `${factId}  ${labelForFact(factId)}`;
        list.appendChild(row);
    }
}

function renderSectionTitle(panel: HTMLElement, text: string): void {
    const title = document.createElement("div");
    title.className = "notebook-section-title";
    title.textContent = text;
    panel.appendChild(title);
}

function renderLines(panel: HTMLElement, lines: Array<[string, string]>): void {
    for (const [labelText, valueText] of lines) {
        const row = document.createElement("div");
        row.className = "notebook-line";
        const label = document.createElement("span");
        label.className = "notebook-label";
        label.textContent = labelText;
        const value = document.createElement("span");
        value.className = "notebook-value";
        value.textContent = valueText;
        row.append(label, value);
        panel.appendChild(row);
    }
}

function renderInfo(panel: HTMLElement, text: string): void {
    const line = document.createElement("div");
    line.className = "notebook-info";
    line.textContent = text;
    panel.appendChild(line);
}

function extractEvidenceIdFromObservedClue(clueId: string): string | null {
    const parts = clueId.split(":");
    if (parts.length < 3) return null;
    const evidenceId = parts[2] ?? "";
    return evidenceId.length > 0 ? evidenceId : null;
}

function labelForEvidence(evidenceId: string): string {
    return EVIDENCE_LABELS[evidenceId] ?? evidenceId;
}

function labelForFact(factId: string): string {
    return FACT_LABELS[factId] ?? factId;
}

function labelForObject(objectId: string): string {
    return OBJECT_LABELS[objectId] ?? objectId;
}
