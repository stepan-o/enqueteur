import type { ConnectingPhase, EnqueteurCaseId } from "../appState";
import type { TranslateFn, TranslationLookupKey } from "../../i18n";

type ConnectingStep = {
    readonly phase: ConnectingPhase;
};

const CONNECTING_STEPS: readonly ConnectingStep[] = [
    { phase: "CASE_LAUNCH" },
    { phase: "SESSION_STARTUP" },
    { phase: "HANDSHAKING" },
    { phase: "WAITING_FOR_BASELINE" },
];

const PHASE_NOTE_KEYS: Record<ConnectingPhase, TranslationLookupKey> = {
    CASE_LAUNCH: "flow.connecting.note.caseLaunch",
    SESSION_STARTUP: "flow.connecting.note.sessionStartup",
    HANDSHAKING: "flow.connecting.note.handshaking",
    WAITING_FOR_BASELINE: "flow.connecting.note.waitingBaseline",
};

export type ConnectingScreenOpts = {
    caseId: EnqueteurCaseId;
    caseLabel?: string;
    phase: ConnectingPhase;
    demoPathLabel?: string;
    blockedStateHint?: string;
    warningMessage?: string;
    onBackToCases: () => void;
    onBackToMenu: () => void;
    t: TranslateFn;
};

export function renderConnectingScreen(opts: ConnectingScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-connecting";

    const shell = document.createElement("div");
    shell.className = "flow-screen-shell";

    const header = document.createElement("div");
    header.className = "flow-screen-header";

    const meta = document.createElement("div");
    meta.className = "flow-screen-meta";

    const caseChip = document.createElement("span");
    caseChip.className = "flow-pill flow-pill-case";
    caseChip.textContent = opts.caseLabel ?? opts.caseId;
    meta.appendChild(caseChip);

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = opts.t("flow.connecting.title");

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = opts.t("flow.connecting.preparingCase", { caseLabel: opts.caseLabel ?? opts.caseId });

    const copy = document.createElement("div");
    copy.className = "flow-screen-copy";
    copy.append(titleEl, bodyEl);

    const steps = document.createElement("ol");
    steps.className = "flow-connection-steps flow-screen-surface";

    const activeStepIdx = CONNECTING_STEPS.findIndex((step) => step.phase === opts.phase);
    for (let idx = 0; idx < CONNECTING_STEPS.length; idx += 1) {
        const step = CONNECTING_STEPS[idx];
        const item = document.createElement("li");
        item.className = "flow-connection-step";
        if (idx < activeStepIdx) {
            item.dataset.status = "done";
        } else if (idx === activeStepIdx) {
            item.dataset.status = "active";
        } else {
            item.dataset.status = "pending";
        }
        item.textContent = opts.t(stepLabelKey(step.phase));
        steps.appendChild(item);
    }

    const note = document.createElement("p");
    note.className = "flow-screen-note flow-screen-surface flow-screen-surface-muted";
    note.textContent = opts.t(PHASE_NOTE_KEYS[opts.phase]);

    const demoPath = opts.demoPathLabel
        ? document.createElement("p")
        : null;
    if (demoPath) {
        demoPath.className = "flow-screen-note flow-screen-surface flow-screen-surface-muted";
        demoPath.textContent = opts.t("flow.connecting.demoRoute", { label: opts.demoPathLabel });
    }

    const blockedHint = opts.blockedStateHint
        ? document.createElement("p")
        : null;
    if (blockedHint) {
        blockedHint.className = "flow-screen-note flow-screen-surface flow-screen-surface-accent";
        blockedHint.textContent = opts.blockedStateHint ?? "";
    }

    const warning = opts.warningMessage
        ? document.createElement("p")
        : null;
    if (warning) {
        warning.className = "flow-screen-note flow-screen-surface flow-screen-surface-warning";
        warning.textContent = formatWarning(opts.warningMessage ?? "", opts.t);
    }

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(makeActionButton(opts.t("flow.connecting.action.backToCases"), opts.onBackToCases, "flow-action-btn-secondary"));
    actions.appendChild(makeActionButton(opts.t("flow.connecting.action.mainMenu"), opts.onBackToMenu, "flow-action-btn-secondary"));

    const supportStack = document.createElement("div");
    supportStack.className = "flow-screen-support-stack";
    supportStack.appendChild(note);
    if (demoPath) {
        supportStack.appendChild(demoPath);
    }
    if (blockedHint) {
        supportStack.appendChild(blockedHint);
    }
    if (warning) {
        supportStack.appendChild(warning);
    }

    header.append(meta, copy);
    shell.append(header, steps);
    if (supportStack.childElementCount > 0) {
        shell.appendChild(supportStack);
    }
    shell.appendChild(actions);
    section.appendChild(shell);
    return section;
}

function formatWarning(raw: string, t: TranslateFn): string {
    const normalized = raw.trim();
    const match = normalized.match(/^Live warning \(([^)]+)\):\s*(.+)$/);
    if (match) {
        const [, code, message] = match;
        return t("flow.connecting.connectionNote", { message, code });
    }
    return normalized;
}

function stepLabelKey(phase: ConnectingPhase): TranslationLookupKey {
    if (phase === "CASE_LAUNCH") return "flow.connecting.step.caseLaunch";
    if (phase === "SESSION_STARTUP") return "flow.connecting.step.sessionStartup";
    if (phase === "HANDSHAKING") return "flow.connecting.step.handshaking";
    return "flow.connecting.step.waitingBaseline";
}

function makeActionButton(label: string, onClick: () => void, variantClass = ""): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = variantClass ? `flow-action-btn ${variantClass}` : "flow-action-btn";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    return btn;
}
