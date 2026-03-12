import type { TranslateFn } from "../../i18n";

export type MainMenuScreenOpts = {
    onCases: () => void;
    t: TranslateFn;
};

export function renderMainMenuScreen(opts: MainMenuScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-menu";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = opts.t("flow.mainMenu.title");

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = opts.t("flow.mainMenu.body");

    const actions = document.createElement("div");
    actions.className = "flow-actions flow-menu-actions";

    const casesBtn = document.createElement("button");
    casesBtn.type = "button";
    casesBtn.className = "flow-action-btn";
    casesBtn.textContent = opts.t("flow.mainMenu.startCase");
    casesBtn.addEventListener("click", opts.onCases);
    actions.appendChild(casesBtn);

    const placeholder = document.createElement("p");
    placeholder.className = "flow-screen-note flow-menu-placeholder";
    placeholder.textContent = opts.t("flow.mainMenu.placeholder");

    section.appendChild(titleEl);
    section.appendChild(bodyEl);
    section.appendChild(actions);
    section.appendChild(placeholder);

    return section;
}
