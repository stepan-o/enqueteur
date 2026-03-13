import type { EnqueteurCaseId } from "../appState";
import type { PreGameCaseEntry } from "../cases/caseCatalog";
import type { TranslateFn } from "../../i18n";

export type CaseSelectScreenOpts = {
    cases: readonly PreGameCaseEntry[];
    onBack: () => void;
    onPickCase: (caseId: EnqueteurCaseId) => void;
    t: TranslateFn;
};

export function renderCaseSelectScreen(opts: CaseSelectScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = opts.t("flow.caseSelect.title");

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = opts.t("flow.caseSelect.body");

    const caseGrid = document.createElement("div");
    caseGrid.className = "flow-case-grid";

    for (const entry of opts.cases) {
        caseGrid.appendChild(makeCaseCard(entry, opts.onPickCase, opts.t));
    }

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(makeActionButton(opts.t("flow.caseSelect.backToMenu"), opts.onBack));

    section.appendChild(titleEl);
    section.appendChild(bodyEl);
    section.appendChild(caseGrid);
    section.appendChild(actions);
    return section;
}

function makeCaseCard(
    entry: PreGameCaseEntry,
    onPickCase: (caseId: EnqueteurCaseId) => void,
    t: TranslateFn
): HTMLButtonElement {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "flow-case-card";

    const code = document.createElement("span");
    code.className = "flow-case-title";
    code.textContent = entry.code;

    const label = document.createElement("span");
    label.className = "flow-case-sub";
    label.textContent = t(entry.labelKey);

    const subtitle = document.createElement("span");
    subtitle.className = "flow-screen-note";
    subtitle.textContent = t(entry.subtitleKey);

    const demoRoute = document.createElement("span");
    demoRoute.className = "flow-screen-note";
    demoRoute.textContent = t("flow.caseSelect.defaultDemoRoute", { title: t(entry.defaultDemoPath.titleKey) });

    const demoSummary = document.createElement("span");
    demoSummary.className = "flow-screen-note";
    demoSummary.textContent = t(entry.defaultDemoPath.summaryKey);

    card.appendChild(code);
    card.appendChild(label);
    card.appendChild(subtitle);
    card.appendChild(demoRoute);
    card.appendChild(demoSummary);
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
