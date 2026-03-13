import type { TranslateFn } from "../../i18n";

export type MainMenuScreenOpts = {
    onCases: () => void;
    t: TranslateFn;
};

export function renderMainMenuScreen(opts: MainMenuScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-menu";

    const shell = document.createElement("div");
    shell.className = "flow-screen-shell";

    const header = document.createElement("div");
    header.className = "flow-screen-header";

    const kicker = document.createElement("span");
    kicker.className = "flow-screen-kicker";
    kicker.textContent = "Enqueteur";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = opts.t("flow.mainMenu.title");

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = opts.t("flow.mainMenu.body");

    const copy = document.createElement("div");
    copy.className = "flow-screen-copy";
    copy.append(titleEl, bodyEl);

    const actions = document.createElement("div");
    actions.className = "flow-actions flow-menu-actions";

    const casesBtn = document.createElement("button");
    casesBtn.type = "button";
    casesBtn.className = "flow-action-btn flow-action-btn-primary";
    casesBtn.textContent = opts.t("flow.mainMenu.startCase");
    casesBtn.addEventListener("click", opts.onCases);
    actions.appendChild(casesBtn);

    const placeholder = document.createElement("div");
    placeholder.className = "flow-screen-surface flow-screen-surface-muted flow-menu-placeholder";

    const placeholderNote = document.createElement("p");
    placeholderNote.className = "flow-screen-note flow-screen-note-compact";
    placeholderNote.textContent = opts.t("flow.mainMenu.placeholder");
    placeholder.appendChild(placeholderNote);

    header.append(kicker, copy);
    shell.append(header, actions, placeholder);
    section.appendChild(shell);

    return section;
}
