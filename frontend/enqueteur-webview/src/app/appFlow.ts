import { boot, type ViewerHandle } from "./boot";
import {
    AppStateStore,
    beginBootFlow,
    type AppState,
    type EnqueteurCaseId,
} from "./appState";

export type AppFlowOpts = {
    mountEl: HTMLElement;
    loadingDurationMs?: number;
};

export type AppFlowHandle = {
    getState: () => AppState;
    transition: (next: AppState) => void;
    destroy: () => void;
};

export function mountAppFlow(opts: AppFlowOpts): AppFlowHandle {
    const root = document.createElement("div");
    root.className = "app-flow";

    const preGameLayer = document.createElement("div");
    preGameLayer.className = "app-flow-layer app-flow-layer-pregame";

    const liveLayer = document.createElement("div");
    liveLayer.className = "app-flow-layer app-flow-layer-live";

    root.appendChild(preGameLayer);
    root.appendChild(liveLayer);
    opts.mountEl.appendChild(root);

    const stateStore = new AppStateStore({ kind: "BOOT" });
    let viewer: ViewerHandle | null = null;

    const render = (state: AppState): void => {
        preGameLayer.innerHTML = "";

        if (state.kind === "LIVE_GAME") {
            preGameLayer.style.display = "none";
            liveLayer.style.display = "block";
            mountLiveGameShell(state.caseId);
            return;
        }

        preGameLayer.style.display = "flex";
        liveLayer.style.display = "none";
        viewer?.setVisible(false);

        switch (state.kind) {
            case "BOOT":
                preGameLayer.appendChild(renderScreen("BOOT", "Preparing Enqueteur shell..."));
                break;
            case "LOADING":
                preGameLayer.appendChild(
                    renderScreen(
                        "Loading",
                        "Loading frontend systems and UI shell.",
                        [renderLogo(), renderPulseBar()]
                    )
                );
                break;
            case "MAIN_MENU":
                preGameLayer.appendChild(renderMainMenu({
                    onStart: () => stateStore.transition({ kind: "CASE_SELECT" }),
                }));
                break;
            case "CASE_SELECT":
                preGameLayer.appendChild(
                    renderCaseSelect({
                        onBack: () => stateStore.transition({ kind: "MAIN_MENU" }),
                        onPickCase: (caseId) => stateStore.transition({ kind: "CONNECTING", caseId }),
                    })
                );
                break;
            case "CONNECTING":
                preGameLayer.appendChild(
                    renderConnecting({
                        caseId: state.caseId,
                        onBackToCases: () => stateStore.transition({ kind: "CASE_SELECT" }),
                        onBackToMenu: () => stateStore.transition({ kind: "MAIN_MENU" }),
                    })
                );
                break;
            case "ERROR":
                preGameLayer.appendChild(
                    renderErrorScreen({
                        message: state.message,
                        recoverTo: state.recoverTo,
                        onRecover: () => {
                            if (state.recoverTo === "CASE_SELECT") {
                                stateStore.transition({ kind: "CASE_SELECT" });
                            } else {
                                stateStore.transition({ kind: "MAIN_MENU" });
                            }
                        },
                    })
                );
                break;
            default:
                preGameLayer.appendChild(
                    renderErrorScreen({
                        message: `Unhandled app state: ${(state as { kind: string }).kind}`,
                        recoverTo: "MAIN_MENU",
                        onRecover: () => stateStore.transition({ kind: "MAIN_MENU" }),
                    })
                );
                break;
        }
    };

    const mountLiveGameShell = (caseId: EnqueteurCaseId): void => {
        if (!viewer) {
            try {
                viewer = boot({
                    mountEl: liveLayer,
                    mode: "live",
                    autoStart: false,
                });
            } catch (err: unknown) {
                const message = err instanceof Error ? err.message : String(err);
                stateStore.transition({
                    kind: "ERROR",
                    message: `Live shell failed to mount for ${caseId}: ${message}`,
                    recoverTo: "MAIN_MENU",
                });
                return;
            }
        }
        viewer.setVisible(true);
    };

    const unsubscribe = stateStore.subscribe(render);
    beginBootFlow(stateStore, { loadingDurationMs: opts.loadingDurationMs });

    return {
        getState: () => stateStore.getState(),
        transition: (next) => stateStore.transition(next),
        destroy: () => {
            unsubscribe();
            viewer?.stop();
            root.remove();
        },
    };
}

function renderScreen(title: string, body: string, children: HTMLElement[] = []): HTMLElement {
    const section = document.createElement("section");
    section.className = "flow-screen";

    const titleEl = document.createElement("h1");
    titleEl.className = "flow-screen-title";
    titleEl.textContent = title;

    const bodyEl = document.createElement("p");
    bodyEl.className = "flow-screen-body";
    bodyEl.textContent = body;

    section.appendChild(titleEl);
    section.appendChild(bodyEl);
    for (const child of children) section.appendChild(child);

    return section;
}

function renderLogo(): HTMLElement {
    const img = document.createElement("img");
    img.className = "flow-logo";
    img.src = "/logo/low-res/enqueteur_logo_title.png";
    img.alt = "Enqueteur";
    return img;
}

function renderPulseBar(): HTMLElement {
    const bar = document.createElement("div");
    bar.className = "flow-pulse";
    return bar;
}

function renderMainMenu(opts: { onStart: () => void }): HTMLElement {
    const section = renderScreen(
        "Enqueteur",
        "Choose a path to begin your investigation."
    );

    const actions = document.createElement("div");
    actions.className = "flow-actions";

    const startBtn = makeActionButton("Cases", opts.onStart);
    actions.appendChild(startBtn);

    section.appendChild(actions);
    return section;
}

function renderCaseSelect(opts: {
    onBack: () => void;
    onPickCase: (caseId: EnqueteurCaseId) => void;
}): HTMLElement {
    const section = renderScreen(
        "Case Selection",
        "Select the case to launch when live session startup becomes available."
    );

    const caseGrid = document.createElement("div");
    caseGrid.className = "flow-case-grid";

    const mbamCard = document.createElement("button");
    mbamCard.type = "button";
    mbamCard.className = "flow-case-card";
    mbamCard.innerHTML = "<span class=\"flow-case-title\">MBAM_01</span><span class=\"flow-case-sub\">Le Petit Vol du Musee</span>";
    mbamCard.addEventListener("click", () => opts.onPickCase("MBAM_01"));

    caseGrid.appendChild(mbamCard);

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(makeActionButton("Back", opts.onBack));

    section.appendChild(caseGrid);
    section.appendChild(actions);

    return section;
}

function renderConnecting(opts: {
    caseId: EnqueteurCaseId;
    onBackToCases: () => void;
    onBackToMenu: () => void;
}): HTMLElement {
    const section = renderScreen(
        "Connecting",
        `Preparing live launch for ${opts.caseId}. Live startup is implemented in later phases.`
    );

    const info = document.createElement("p");
    info.className = "flow-screen-note";
    info.textContent = "No backend call or WebSocket connect is attempted in this phase.";

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(makeActionButton("Back To Cases", opts.onBackToCases));
    actions.appendChild(makeActionButton("Main Menu", opts.onBackToMenu));

    section.appendChild(info);
    section.appendChild(actions);
    return section;
}

function renderErrorScreen(opts: {
    message: string;
    recoverTo?: "MAIN_MENU" | "CASE_SELECT";
    onRecover: () => void;
}): HTMLElement {
    const section = renderScreen("Error", opts.message);

    const info = document.createElement("p");
    info.className = "flow-screen-note";
    info.textContent =
        opts.recoverTo === "CASE_SELECT"
            ? "You can return to case selection."
            : "You can return to the main menu.";

    const actions = document.createElement("div");
    actions.className = "flow-actions";
    actions.appendChild(makeActionButton("Recover", opts.onRecover));

    section.appendChild(info);
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
