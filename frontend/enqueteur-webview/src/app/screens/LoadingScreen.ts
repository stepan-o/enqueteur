export type LoadingScreenOpts = {
    logoSrc?: string;
};

export function renderLoadingScreen(opts: LoadingScreenOpts = {}): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-loading";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = "Preparing Case";

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = "Setting up the investigation space.";

    const logoSlot = document.createElement("div");
    logoSlot.className = "flow-logo-slot";

    const logoSrc = (opts.logoSrc ?? "").trim();
    if (logoSrc) {
        const img = document.createElement("img");
        img.className = "flow-logo";
        img.src = logoSrc;
        img.alt = "Enqueteur";
        img.onerror = () => {
            logoSlot.innerHTML = "";
            logoSlot.appendChild(makeLogoPlaceholder());
        };
        logoSlot.appendChild(img);
    } else {
        logoSlot.appendChild(makeLogoPlaceholder());
    }

    const pulse = document.createElement("div");
    pulse.className = "flow-pulse";

    const note = document.createElement("p");
    note.className = "flow-screen-note";
    note.textContent = "Logo placeholder: final key art can be dropped in here.";

    section.appendChild(titleEl);
    section.appendChild(bodyEl);
    section.appendChild(logoSlot);
    section.appendChild(pulse);
    section.appendChild(note);

    return section;
}

function makeLogoPlaceholder(): HTMLElement {
    const placeholder = document.createElement("div");
    placeholder.className = "flow-logo-placeholder";
    placeholder.textContent = "ENQUETEUR";
    return placeholder;
}
