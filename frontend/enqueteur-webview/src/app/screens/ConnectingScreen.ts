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

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = opts.t("flow.connecting.title");

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = opts.t("flow.connecting.preparingCase", { caseLabel: opts.caseLabel ?? opts.caseId });

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
        item.textContent = opts.t(stepLabelKey(step.phase));
        steps.appendChild(item);
    }

    const note = document.createElement("p");
    note.className = "flow-screen-note";
    note.textContent = opts.t(PHASE_NOTE_KEYS[opts.phase]);

    const demoPath = opts.demoPathLabel
        ? document.createElement("p")
        : null;
    if (demoPath) {
        demoPath.className = "flow-screen-note";
        demoPath.textContent = opts.t("flow.connecting.demoRoute", { label: opts.demoPathLabel });
    }

    const blockedHint = opts.blockedStateHint
        ? document.createElement("p")
        : null;
    if (blockedHint) {
        blockedHint.className = "flow-screen-note";
        blockedHint.textContent = opts.blockedStateHint ?? "";
    }

    const warning = opts.warningMessage
        ? document.createElement("p")
        : null;
    if (warning) {
        warning.className = "flow-screen-note";
        warning.textContent = formatWarning(opts.warningMessage ?? "", opts.t);
    }

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(makeActionButton(opts.t("flow.connecting.action.backToCases"), opts.onBackToCases));
    actions.appendChild(makeActionButton(opts.t("flow.connecting.action.mainMenu"), opts.onBackToMenu));

    section.appendChild(titleEl);
    section.appendChild(bodyEl);
    section.appendChild(steps);
    section.appendChild(note);
    if (demoPath) {
        section.appendChild(demoPath);
    }
    if (blockedHint) {
        section.appendChild(blockedHint);
    }
    if (warning) {
        section.appendChild(warning);
    }
    section.appendChild(actions);
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

function makeActionButton(label: string, onClick: () => void): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "flow-action-btn";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    return btn;
}
