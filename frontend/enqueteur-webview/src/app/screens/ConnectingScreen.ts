import type { ConnectingPhase, EnqueteurCaseId } from "../appState";

type ConnectingStep = {
    readonly phase: ConnectingPhase;
    readonly label: string;
};

const CONNECTING_STEPS: readonly ConnectingStep[] = [
    { phase: "CASE_LAUNCH", label: "Case launch in progress" },
    { phase: "SESSION_STARTUP", label: "Session startup in progress" },
    { phase: "WAITING_FOR_BASELINE", label: "Waiting for baseline snapshot" },
];

export type ConnectingScreenOpts = {
    caseId: EnqueteurCaseId;
    phase: ConnectingPhase;
    onBackToCases: () => void;
    onBackToMenu: () => void;
};

export function renderConnectingScreen(opts: ConnectingScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-connecting";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = "Connecting";

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = `Preparing ${opts.caseId} for live play.`;

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
    note.textContent = "Backend launch and transport wiring arrive in the next phases.";

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(makeActionButton("Back To Cases", opts.onBackToCases));
    actions.appendChild(makeActionButton("Main Menu", opts.onBackToMenu));

    section.appendChild(titleEl);
    section.appendChild(bodyEl);
    section.appendChild(steps);
    section.appendChild(note);
    section.appendChild(actions);
    return section;
}

function makeActionButton(label: string, onClick: () => void): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "flow-action-btn";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    return btn;
}
