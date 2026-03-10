import type { EnqueteurCaseId } from "../appState";
import type { PreGameCaseEntry } from "../cases/caseCatalog";

export type CaseSelectScreenOpts = {
    cases: readonly PreGameCaseEntry[];
    onBack: () => void;
    onPickCase: (caseId: EnqueteurCaseId) => void;
};

export function renderCaseSelectScreen(opts: CaseSelectScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = "Choose A Case";

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = "Pick a case to begin a live investigation.";

    const caseGrid = document.createElement("div");
    caseGrid.className = "flow-case-grid";

    for (const entry of opts.cases) {
        caseGrid.appendChild(makeCaseCard(entry, opts.onPickCase));
    }

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(makeActionButton("Back To Menu", opts.onBack));

    section.appendChild(titleEl);
    section.appendChild(bodyEl);
    section.appendChild(caseGrid);
    section.appendChild(actions);
    return section;
}

function makeCaseCard(
    entry: PreGameCaseEntry,
    onPickCase: (caseId: EnqueteurCaseId) => void
): HTMLButtonElement {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "flow-case-card";

    const code = document.createElement("span");
    code.className = "flow-case-title";
    code.textContent = entry.code;

    const label = document.createElement("span");
    label.className = "flow-case-sub";
    label.textContent = entry.label;

    const subtitle = document.createElement("span");
    subtitle.className = "flow-screen-note";
    subtitle.textContent = entry.subtitle;

    card.appendChild(code);
    card.appendChild(label);
    card.appendChild(subtitle);
    card.addEventListener("click", () => onPickCase(entry.caseId));
    return card;
}

function makeActionButton(label: string, onClick: () => void): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "flow-action-btn";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    return btn;
}
