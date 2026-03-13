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
    section.className = "flow-screen flow-screen-case-select";

    const shell = document.createElement("div");
    shell.className = "flow-screen-shell";

    const header = document.createElement("div");
    header.className = "flow-screen-header";

    const kicker = document.createElement("span");
    kicker.className = "flow-screen-kicker";
    kicker.textContent = "Enqueteur";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = opts.t("flow.caseSelect.title");

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = opts.t("flow.caseSelect.body");

    const copy = document.createElement("div");
    copy.className = "flow-screen-copy";
    copy.append(titleEl, bodyEl);

    const caseGrid = document.createElement("div");
    caseGrid.className = "flow-case-grid";

    for (const entry of opts.cases) {
        caseGrid.appendChild(makeCaseCard(entry, opts.onPickCase, opts.t));
    }

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(makeActionButton(opts.t("flow.caseSelect.backToMenu"), opts.onBack, "flow-action-btn-secondary"));

    header.append(kicker, copy);
    shell.append(header, caseGrid, actions);
    section.appendChild(shell);
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

    const meta = document.createElement("div");
    meta.className = "flow-case-meta";

    const code = document.createElement("span");
    code.className = "flow-case-title flow-pill";
    code.textContent = entry.code;

    const label = document.createElement("span");
    label.className = "flow-case-sub";
    label.textContent = t(entry.labelKey);

    const subtitle = document.createElement("span");
    subtitle.className = "flow-screen-note flow-case-subtitle";
    subtitle.textContent = t(entry.subtitleKey);

    const demoRoute = document.createElement("span");
    demoRoute.className = "flow-screen-note flow-case-route";
    demoRoute.textContent = t("flow.caseSelect.defaultDemoRoute", { title: t(entry.defaultDemoPath.titleKey) });

    const demoSummary = document.createElement("span");
    demoSummary.className = "flow-screen-note flow-case-summary";
    demoSummary.textContent = t(entry.defaultDemoPath.summaryKey);

    meta.appendChild(code);
    card.append(meta, label, subtitle, demoRoute, demoSummary);
    card.addEventListener("click", () => onPickCase(entry.caseId));
    return card;
}

function makeActionButton(label: string, onClick: () => void, variantClass = ""): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = variantClass ? `flow-action-btn ${variantClass}` : "flow-action-btn";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    return btn;
}
