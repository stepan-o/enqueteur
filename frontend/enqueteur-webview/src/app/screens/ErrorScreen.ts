import type { AppErrorCode, AppRecoverTarget } from "../appState";
import type { TranslateFn, TranslationLookupKey } from "../../i18n";

export type ErrorScreenOpts = {
    code: AppErrorCode;
    message: string;
    recoverTo?: AppRecoverTarget;
    onRetry?: () => void;
    retryLabel?: string;
    onRecover: () => void;
    t: TranslateFn;
};

const ERROR_TITLE_KEYS: Record<AppErrorCode, TranslationLookupKey> = {
    LAUNCH_FAILURE: "flow.error.body.launchFailure",
    CONNECTION_FAILURE: "flow.error.body.connectionFailure",
    STARTUP_INCOMPATIBILITY: "flow.error.body.startupIncompatibility",
    UNEXPECTED_STATE: "flow.error.body.unexpectedState",
};

export function renderErrorScreen(opts: ErrorScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-error";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = opts.t("flow.error.title");

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = opts.t(ERROR_TITLE_KEYS[opts.code]);

    const detail = document.createElement("p");
    detail.className = "flow-screen-note";
    detail.textContent = humanizeErrorMessage(opts.message, opts.t);

    const hint = document.createElement("p");
    hint.className = "flow-screen-note";
    hint.textContent =
        opts.recoverTo === "CASE_SELECT"
            ? opts.t("flow.error.hint.caseSelect")
            : opts.t("flow.error.hint.mainMenu");

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    if (opts.onRetry) {
        actions.appendChild(
            makeActionButton(opts.retryLabel ?? defaultRetryLabel(opts.code, opts.t), opts.onRetry)
        );
    }
    actions.appendChild(
        makeActionButton(
            opts.recoverTo === "CASE_SELECT"
                ? opts.t("flow.error.action.backToCases")
                : opts.t("flow.error.action.backToMainMenu"),
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

function defaultRetryLabel(code: AppErrorCode, t: TranslateFn): string {
    if (code === "LAUNCH_FAILURE") return t("flow.error.retry.launchAgain");
    if (code === "CONNECTION_FAILURE") return t("flow.error.retry.reconnect");
    return t("flow.error.retry.default");
}

function humanizeErrorMessage(message: string, t: TranslateFn): string {
    if (message.includes("Launch metadata is missing")) {
        return t("flow.error.detail.launchMetadataMissing");
    }
    if (
        message.includes("KERNEL_HELLO")
        || message.includes("SUBSCRIBED")
        || message.includes("FULL_SNAPSHOT")
        || message.includes("schema mismatch")
        || message.includes("engine mismatch")
    ) {
        return t("flow.error.detail.startupOutOfSync");
    }
    if (message.includes("WebSocket") || message.includes("socket")) {
        return t("flow.error.detail.socketClosed");
    }
    if (message.startsWith("Case launch failed")) {
        return t("flow.error.detail.caseNotOpened");
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
