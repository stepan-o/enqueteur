import type { ConnectingPhase, EnqueteurCaseId } from "../appState";

type ConnectingStep = {
    readonly phase: ConnectingPhase;
    readonly label: string;
};

const CONNECTING_STEPS: readonly ConnectingStep[] = [
    { phase: "CASE_LAUNCH", label: "Opening case file" },
    { phase: "SESSION_STARTUP", label: "Joining live session" },
    { phase: "HANDSHAKING", label: "Confirming session" },
    { phase: "WAITING_FOR_BASELINE", label: "Loading first scene" },
];

const PHASE_NOTES: Record<ConnectingPhase, string> = {
    CASE_LAUNCH: "Creating your run and preparing the case.",
    SESSION_STARTUP: "Case is ready. Opening the live connection.",
    HANDSHAKING: "Connection is open. Verifying the session and joining the stream.",
    WAITING_FOR_BASELINE: "Receiving the initial world state.",
};

export type ConnectingScreenOpts = {
    caseId: EnqueteurCaseId;
    phase: ConnectingPhase;
    warningMessage?: string;
    onBackToCases: () => void;
    onBackToMenu: () => void;
};

export function renderConnectingScreen(opts: ConnectingScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-connecting";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = "Entering Case";

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = `Preparing ${opts.caseId}.`;

    const steps = document.createElement("ol");
    steps.className = "flow-connection-steps";

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
        item.textContent = step.label;
        steps.appendChild(item);
    }

    const note = document.createElement("p");
    note.className = "flow-screen-note";
    note.textContent = PHASE_NOTES[opts.phase];

    const warning = opts.warningMessage
        ? document.createElement("p")
        : null;
    if (warning) {
        warning.className = "flow-screen-note";
        warning.textContent = formatWarning(opts.warningMessage ?? "");
    }

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(makeActionButton("Back To Cases", opts.onBackToCases));
    actions.appendChild(makeActionButton("Main Menu", opts.onBackToMenu));

    section.appendChild(titleEl);
    section.appendChild(bodyEl);
    section.appendChild(steps);
    section.appendChild(note);
    if (warning) {
        section.appendChild(warning);
    }
    section.appendChild(actions);
    return section;
}

function formatWarning(raw: string): string {
    const normalized = raw.trim();
    const match = normalized.match(/^Live warning \(([^)]+)\):\s*(.+)$/);
    if (match) {
        const [, code, message] = match;
        return `Connection note: ${message} (${code}).`;
    }
    return normalized;
}

function makeActionButton(label: string, onClick: () => void): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "flow-action-btn";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    return btn;
}
