import type { AppErrorCode, AppRecoverTarget } from "../appState";

export type ErrorScreenOpts = {
    code: AppErrorCode;
    message: string;
    recoverTo?: AppRecoverTarget;
    onRecover: () => void;
};

const ERROR_TITLES: Record<AppErrorCode, string> = {
    LAUNCH_FAILURE: "Case launch failed",
    CONNECTION_FAILURE: "Live connection failed",
    STARTUP_INCOMPATIBILITY: "Startup incompatibility",
    UNEXPECTED_STATE: "Unexpected startup state",
};

export function renderErrorScreen(opts: ErrorScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-error";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = "Error";

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = ERROR_TITLES[opts.code];

    const detail = document.createElement("p");
    detail.className = "flow-screen-note";
    detail.textContent = opts.message;

    const hint = document.createElement("p");
    hint.className = "flow-screen-note";
    hint.textContent =
        opts.recoverTo === "CASE_SELECT"
            ? "Return to case selection and retry launch."
            : "Return to the main menu.";

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(
        makeActionButton(
            opts.recoverTo === "CASE_SELECT" ? "Back To Cases" : "Back To Main Menu",
            opts.onRecover
        )
    );

    section.appendChild(titleEl);
    section.appendChild(bodyEl);
    section.appendChild(detail);
    section.appendChild(hint);
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
