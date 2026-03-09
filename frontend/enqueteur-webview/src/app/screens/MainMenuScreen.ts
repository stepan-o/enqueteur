export type MainMenuScreenOpts = {
    onCases: () => void;
};

export function renderMainMenuScreen(opts: MainMenuScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-menu";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = "Enqueteur";

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = "Begin your investigation.";

    const actions = document.createElement("div");
    actions.className = "flow-actions flow-menu-actions";

    const casesBtn = document.createElement("button");
    casesBtn.type = "button";
    casesBtn.className = "flow-action-btn";
    casesBtn.textContent = "Cases";
    casesBtn.addEventListener("click", opts.onCases);
    actions.appendChild(casesBtn);

    const placeholder = document.createElement("p");
    placeholder.className = "flow-screen-note flow-menu-placeholder";
    placeholder.textContent = "More menu options can be added here in later phases.";

    section.appendChild(titleEl);
    section.appendChild(bodyEl);
    section.appendChild(actions);
    section.appendChild(placeholder);

    return section;
}
