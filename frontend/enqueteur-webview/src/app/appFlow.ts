import { boot, type ViewerHandle } from "./boot";
import {
    AppStateStore,
    beginBootFlow,
    type AppState,
    type EnqueteurCaseId,
} from "./appState";
import { PRE_GAME_CASES } from "./cases/caseCatalog";
import { renderLoadingScreen } from "./screens/LoadingScreen";
import { renderCaseSelectScreen } from "./screens/CaseSelectScreen";
import { renderConnectingScreen } from "./screens/ConnectingScreen";
import { renderErrorScreen } from "./screens/ErrorScreen";
import { renderMainMenuScreen } from "./screens/MainMenuScreen";

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
                    renderLoadingScreen({ logoSrc: "/logo/low-res/enqueteur_logo_title.png" })
                );
                break;
            case "MAIN_MENU":
                preGameLayer.appendChild(renderMainMenuScreen({
                    onCases: () => stateStore.transition({ kind: "CASE_SELECT" }),
                }));
                break;
            case "CASE_SELECT":
                preGameLayer.appendChild(
                    renderCaseSelectScreen({
                        cases: PRE_GAME_CASES,
                        onBack: () => stateStore.transition({ kind: "MAIN_MENU" }),
                        onPickCase: (caseId) =>
                            stateStore.transition({ kind: "CONNECTING", caseId, phase: "CASE_LAUNCH" }),
                    })
                );
                break;
            case "CONNECTING":
                preGameLayer.appendChild(
                    renderConnectingScreen({
                        caseId: state.caseId,
                        phase: state.phase,
                        onBackToCases: () => stateStore.transition({ kind: "CASE_SELECT" }),
                        onBackToMenu: () => stateStore.transition({ kind: "MAIN_MENU" }),
                    })
                );
                break;
            case "ERROR":
                preGameLayer.appendChild(
                    renderErrorScreen({
                        code: state.code,
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
                        code: "UNEXPECTED_STATE",
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
                    code: "STARTUP_INCOMPATIBILITY",
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
