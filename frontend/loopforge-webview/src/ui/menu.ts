// src/ui/menu.ts
type MenuScreen = "main" | "factory" | "dev" | "cinematic" | "about_factory" | "about_project" | "contact";

export type MenuRun = {
    id: string;
    label: string;
    detail?: string;
    baseUrl: string;
};

export type MenuAction =
    | { type: "GO_FACTORY" }
    | { type: "OPEN_LIVE_SIM4" }
    | { type: "OPEN_LIVE_SIM_SIM" }
    | { type: "OPEN_DEV" }
    | { type: "OPEN_CINEMATIC" }
    | { type: "BACK_MAIN" }
    | { type: "ABOUT_FACTORY" }
    | { type: "ABOUT_PROJECT" }
    | { type: "CONTACT" }
    | { type: "RUN_SELECTED"; run: MenuRun }
    | { type: "SOUND_TOGGLE"; enabled: boolean };

export type MenuHandle = {
    root: HTMLElement;
    setScreen: (screen: MenuScreen) => void;
    setFactoryBackground: (url: string) => void;
    setDevBackground: (url: string) => void;
    setRuns: (runs: MenuRun[]) => void;
    setSoundEnabled: (enabled: boolean) => void;
};

export function createMenu(onAction: (action: MenuAction) => void): MenuHandle {
    const root = document.createElement("div");
    root.className = "menu-root";

    const screens: Record<MenuScreen, HTMLElement> = {
        main: buildMainScreen(onAction),
        factory: buildFactoryScreen(onAction),
        dev: buildDevScreen(onAction),
        cinematic: buildInfoScreen("Cinematic View", "Cinematic mode is being forged. Check back soon.", onAction),
        about_factory: buildInfoScreen(
            "About The Factory",
            "Loopforge is a speculative AI brain factory where agents collaborate on cognitive production lines.",
            onAction
        ),
        about_project: buildInfoScreen(
            "About This Project",
            "Loopforge explores multi-agent simulation, worldbuilding, and narrative systems in a living factory.",
            onAction
        ),
        contact: buildInfoScreen(
            "Contact The Creator",
            "Contact details will be added soon. For now, follow the project updates in the main channels.",
            onAction
        ),
    };

    Object.values(screens).forEach((screen) => root.appendChild(screen));

    const soundToggle = buildSoundToggle(onAction);
    root.appendChild(soundToggle);

    const setScreen = (screen: MenuScreen) => {
        Object.entries(screens).forEach(([key, node]) => {
            if (key === screen) node.classList.add("is-active");
            else node.classList.remove("is-active");
        });
    };

    const setFactoryBackground = (url: string) => {
        const bg = screens.factory.querySelector(".menu-bg") as HTMLElement | null;
        if (bg) bg.style.backgroundImage = `url("${url}")`;
    };

    const setDevBackground = (url: string) => {
        const bg = screens.dev.querySelector(".menu-bg") as HTMLElement | null;
        if (bg) bg.style.backgroundImage = `url("${url}")`;
    };

    const setRuns = (runs: MenuRun[]) => {
        const list = screens.dev.querySelector(".menu-run-list") as HTMLElement | null;
        if (!list) return;
        list.innerHTML = "";
        if (runs.length === 0) {
            const empty = document.createElement("div");
            empty.className = "menu-empty";
            empty.textContent = "No recorded runs found.";
            list.appendChild(empty);
            return;
        }
        for (const run of runs) {
            const btn = document.createElement("button");
            btn.className = "menu-option menu-run";
            btn.type = "button";
            btn.innerHTML = `<span class="menu-run-title">${run.label}</span>${
                run.detail ? `<span class="menu-run-detail">${run.detail}</span>` : ""
            }`;
            btn.addEventListener("click", () => onAction({ type: "RUN_SELECTED", run }));
            list.appendChild(btn);
        }
    };

    const setSoundEnabled = (enabled: boolean) => {
        soundToggle.dataset.enabled = enabled ? "true" : "false";
    };

    setScreen("main");
    setSoundEnabled(false);

    return {
        root,
        setScreen,
        setFactoryBackground,
        setDevBackground,
        setRuns,
        setSoundEnabled,
    };
}

function buildMainScreen(onAction: (action: MenuAction) => void): HTMLElement {
    const screen = document.createElement("section");
    screen.className = "menu-screen menu-main is-active";

    const backdrop = document.createElement("div");
    backdrop.className = "menu-backdrop";
    screen.appendChild(backdrop);

    const content = document.createElement("div");
    content.className = "menu-content";

    const logoShell = document.createElement("div");
    logoShell.className = "logo-shell";
    const logo = document.createElement("img");
    logo.className = "menu-logo";
    logo.src = "/assets/logo/loopforge_factory_logo_main.png";
    logo.alt = "Loopforge";
    logoShell.appendChild(logo);
    content.appendChild(logoShell);

    const list = document.createElement("div");
    list.className = "menu-list";

    list.appendChild(makeMenuButton("Go to factory", () => onAction({ type: "GO_FACTORY" })));
    list.appendChild(makeMenuButton("About the factory", () => onAction({ type: "ABOUT_FACTORY" })));
    list.appendChild(makeMenuButton("About this project", () => onAction({ type: "ABOUT_PROJECT" })));
    list.appendChild(makeMenuButton("Contact the creator", () => onAction({ type: "CONTACT" })));

    content.appendChild(list);
    screen.appendChild(content);

    return screen;
}

function buildFactoryScreen(onAction: (action: MenuAction) => void): HTMLElement {
    const screen = document.createElement("section");
    screen.className = "menu-screen menu-factory";

    const bg = document.createElement("div");
    bg.className = "menu-bg";
    screen.appendChild(bg);

    const overlay = document.createElement("div");
    overlay.className = "menu-overlay";
    screen.appendChild(overlay);

    const content = document.createElement("div");
    content.className = "menu-content menu-content-bottom";

    const title = document.createElement("div");
    title.className = "menu-title";
    title.textContent = "Select Factory Mode";
    content.appendChild(title);

    const list = document.createElement("div");
    list.className = "menu-list";
    list.appendChild(makeMenuButton("LIVE (sim4 dev)", () => onAction({ type: "OPEN_LIVE_SIM4" })));
    list.appendChild(makeMenuButton("LIVE (sim_sim)", () => onAction({ type: "OPEN_LIVE_SIM_SIM" })));
    list.appendChild(makeMenuButton("Cinematic view", () => onAction({ type: "OPEN_CINEMATIC" })));
    list.appendChild(makeMenuButton("Dev view", () => onAction({ type: "OPEN_DEV" })));
    list.appendChild(makeMenuButton("Back to main menu", () => onAction({ type: "BACK_MAIN" })));

    content.appendChild(list);
    screen.appendChild(content);

    return screen;
}

function buildDevScreen(onAction: (action: MenuAction) => void): HTMLElement {
    const screen = document.createElement("section");
    screen.className = "menu-screen menu-dev";

    const bg = document.createElement("div");
    bg.className = "menu-bg";
    screen.appendChild(bg);

    const overlay = document.createElement("div");
    overlay.className = "menu-overlay";
    screen.appendChild(overlay);

    const content = document.createElement("div");
    content.className = "menu-content menu-content-right";

    const title = document.createElement("div");
    title.className = "menu-title";
    title.textContent = "Recorded Runs";
    content.appendChild(title);

    const list = document.createElement("div");
    list.className = "menu-run-list";
    content.appendChild(list);

    const back = makeMenuButton("Back to factory menu", () => onAction({ type: "GO_FACTORY" }));
    back.classList.add("menu-back");
    content.appendChild(back);

    screen.appendChild(content);

    return screen;
}

function buildInfoScreen(titleText: string, bodyText: string, onAction: (action: MenuAction) => void): HTMLElement {
    const screen = document.createElement("section");
    screen.className = "menu-screen menu-info";

    const backdrop = document.createElement("div");
    backdrop.className = "menu-backdrop";
    screen.appendChild(backdrop);

    const content = document.createElement("div");
    content.className = "menu-content menu-content-center";

    const title = document.createElement("div");
    title.className = "menu-title";
    title.textContent = titleText;
    content.appendChild(title);

    const body = document.createElement("div");
    body.className = "menu-body";
    body.textContent = bodyText;
    content.appendChild(body);

    const back = makeMenuButton("Back to main menu", () => onAction({ type: "BACK_MAIN" }));
    back.classList.add("menu-back");
    content.appendChild(back);

    screen.appendChild(content);

    return screen;
}

function makeMenuButton(label: string, onClick: () => void): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.className = "menu-option";
    btn.type = "button";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    return btn;
}

function buildSoundToggle(onAction: (action: MenuAction) => void): HTMLElement {
    const btn = document.createElement("button");
    btn.className = "sound-toggle";
    btn.type = "button";
    btn.dataset.enabled = "false";
    btn.innerHTML = `
        <span class="sound-icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 9v6h4l5 4V5L8 9H4z" />
                <path class="sound-slash" d="M19 5L5 19" />
            </svg>
        </span>
        <span class="sound-label">Sound</span>
    `;
    btn.addEventListener("click", () => {
        const enabled = btn.dataset.enabled !== "true";
        btn.dataset.enabled = enabled ? "true" : "false";
        onAction({ type: "SOUND_TOGGLE", enabled });
    });
    return btn;
}
