import type { AppErrorCode, AppRecoverTarget } from "../appState";

export type ErrorScreenOpts = {
    code: AppErrorCode;
    message: string;
    recoverTo?: AppRecoverTarget;
    onRetry?: () => void;
    retryLabel?: string;
    onRecover: () => void;
};

const ERROR_TITLES: Record<AppErrorCode, string> = {
    LAUNCH_FAILURE: "Couldn't start this case",
    CONNECTION_FAILURE: "Connection failed",
    STARTUP_INCOMPATIBILITY: "Version mismatch",
    UNEXPECTED_STATE: "Startup interrupted",
};

export function renderErrorScreen(opts: ErrorScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-error";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = "Something Went Wrong";

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = ERROR_TITLES[opts.code];

    const detail = document.createElement("p");
    detail.className = "flow-screen-note";
    detail.textContent = humanizeErrorMessage(opts.message);

    const hint = document.createElement("p");
    hint.className = "flow-screen-note";
    hint.textContent =
        opts.recoverTo === "CASE_SELECT"
            ? "Return to case selection and try again."
            : "Return to the main menu and restart the case.";

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    if (opts.onRetry) {
        actions.appendChild(
            makeActionButton(opts.retryLabel ?? defaultRetryLabel(opts.code), opts.onRetry)
        );
    }
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

function defaultRetryLabel(code: AppErrorCode): string {
    if (code === "LAUNCH_FAILURE") return "Try Launch Again";
    if (code === "CONNECTION_FAILURE") return "Try Reconnecting";
    return "Retry";
}

function humanizeErrorMessage(message: string): string {
    if (message.includes("Launch metadata is missing")) {
        return "Case setup was interrupted. Please pick the case again.";
    }
    if (
        message.includes("KERNEL_HELLO")
        || message.includes("SUBSCRIBED")
        || message.includes("FULL_SNAPSHOT")
        || message.includes("schema mismatch")
        || message.includes("engine mismatch")
    ) {
        return "This client and server are not in sync for startup. Return to menu and relaunch.";
    }
    if (message.includes("WebSocket") || message.includes("socket")) {
        return "The live connection closed before the case was ready.";
    }
    if (message.startsWith("Case launch failed")) {
        return "The case could not be opened right now.";
    }
    return message;
}

function makeActionButton(label: string, onClick: () => void): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "flow-action-btn";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    return btn;
}
