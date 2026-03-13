import type { TranslateFn } from "../../i18n";

export type LoadingScreenOpts = {
    logoSrc?: string;
    t: TranslateFn;
};

export function renderLoadingScreen(opts: LoadingScreenOpts): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen flow-screen-loading";

    const shell = document.createElement("div");
    shell.className = "flow-screen-shell";

    const header = document.createElement("div");
    header.className = "flow-screen-header flow-screen-header-loading";

    const kicker = document.createElement("span");
    kicker.className = "flow-screen-kicker";
    kicker.textContent = "Enqueteur";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = opts.t("flow.loading.title");

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = opts.t("flow.loading.body");

    const copy = document.createElement("div");
    copy.className = "flow-screen-copy";
    copy.append(titleEl, bodyEl);

    const logoSlot = document.createElement("div");
    logoSlot.className = "flow-logo-slot";

    const logoFrame = document.createElement("div");
    logoFrame.className = "flow-logo-frame";
    logoFrame.appendChild(logoSlot);

    const logoSrc = (opts.logoSrc ?? "").trim();
    if (logoSrc) {
        const img = document.createElement("img");
        img.className = "flow-logo";
        img.src = logoSrc;
        img.alt = opts.t("flow.loading.logoAlt");
        img.onerror = () => {
            logoSlot.innerHTML = "";
            logoSlot.appendChild(makeLogoPlaceholder(opts.t));
        };
        logoSlot.appendChild(img);
    } else {
        logoSlot.appendChild(makeLogoPlaceholder(opts.t));
    }

    const pulse = document.createElement("div");
    pulse.className = "flow-pulse";

    const note = document.createElement("p");
    note.className = "flow-screen-note flow-screen-note-compact";
    note.textContent = opts.t("flow.loading.note");

    const statusCard = document.createElement("div");
    statusCard.className = "flow-screen-surface flow-screen-surface-accent";
    statusCard.append(pulse, note);

    header.append(kicker, logoFrame, copy);
    shell.append(header, statusCard);
    section.appendChild(shell);

    return section;
}

function makeLogoPlaceholder(t: TranslateFn): HTMLElement {
    const placeholder = document.createElement("div");
    placeholder.className = "flow-logo-placeholder";
    placeholder.textContent = t("flow.loading.logoPlaceholder");
    return placeholder;
}
