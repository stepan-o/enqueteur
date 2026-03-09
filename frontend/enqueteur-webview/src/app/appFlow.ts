import {
    AppStateStore,
    beginBootFlow,
    type AppRecoverTarget,
    type AppState,
    type EnqueteurCaseId,
} from "./appState";
import {
    PRE_GAME_CASES,
    getPreGameCaseEntry,
} from "./cases/caseCatalog";
import {
    CaseLaunchError,
    createCaseLaunchClient,
    type CaseLaunchClient,
    type CaseLaunchRequest,
    type CaseLaunchMetadata,
} from "./api/caseLaunchClient";
import { LaunchSessionStore, type LaunchFailureRecord } from "./launch/launchSessionStore";
import { renderLoadingScreen } from "./screens/LoadingScreen";
import { renderCaseSelectScreen } from "./screens/CaseSelectScreen";
import { renderConnectingScreen } from "./screens/ConnectingScreen";
import { renderErrorScreen } from "./screens/ErrorScreen";
import { renderMainMenuScreen } from "./screens/MainMenuScreen";

export type AppFlowOpts = {
    mountEl: HTMLElement;
    loadingDurationMs?: number;
    createLiveViewer?: (mountEl: HTMLElement) => ViewerHandle | Promise<ViewerHandle>;
    caseLaunchClient?: CaseLaunchClient;
};

export type AppFlowHandle = {
    getState: () => AppState;
    getLaunchMetadata: () => CaseLaunchMetadata | null;
    getLaunchFailure: () => LaunchFailureRecord | null;
    transition: (next: AppState) => void;
    destroy: () => void;
};

type ViewerHandle = import("./boot").ViewerHandle;

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
    const launchSessionStore = new LaunchSessionStore();
    let viewer: ViewerHandle | null = null;
    let bootModulePromise: Promise<typeof import("./boot")> | null = null;
    let mountRevision = 0;
    let destroyed = false;
    let launchRevision = 0;
    let pendingLaunchAbortController: AbortController | null = null;

    const caseLaunchClient = opts.caseLaunchClient ?? createCaseLaunchClient();

    const cancelPendingLaunch = (): void => {
        launchRevision += 1;
        if (pendingLaunchAbortController) {
            pendingLaunchAbortController.abort();
            pendingLaunchAbortController = null;
        }
    };

    const resetLaunchProgress = (): void => {
        launchSessionStore.clearProgress();
    };

    const goToMainMenu = (): void => {
        cancelPendingLaunch();
        resetLaunchProgress();
        stateStore.transition({ kind: "MAIN_MENU" });
    };
    const goToCaseSelect = (): void => {
        cancelPendingLaunch();
        resetLaunchProgress();
        stateStore.transition({ kind: "CASE_SELECT" });
    };
    const beginCaseLaunch = (caseId: EnqueteurCaseId): void => {
        const entry = getPreGameCaseEntry(caseId);
        if (!entry) {
            stateStore.transition({
                kind: "ERROR",
                code: "UNEXPECTED_STATE",
                message: `No launch preset found for case ${caseId}.`,
                recoverTo: "CASE_SELECT",
            });
            return;
        }

        cancelPendingLaunch();
        resetLaunchProgress();
        const attemptRevision = launchRevision;
        const abortController = new AbortController();
        pendingLaunchAbortController = abortController;
        const launchRequest: CaseLaunchRequest = {
            caseId,
            seed: entry.launchPreset.seed,
            difficultyProfile: entry.launchPreset.difficultyProfile,
            mode: entry.launchPreset.mode,
        };
        launchSessionStore.begin(launchRequest);

        stateStore.transition({ kind: "CONNECTING", caseId, phase: "CASE_LAUNCH" });
        void requestCaseLaunch(caseId, attemptRevision, launchRequest, abortController.signal);
    };
    const recoverFromError = (recoverTo?: AppRecoverTarget): void => {
        if (recoverTo === "CASE_SELECT") {
            goToCaseSelect();
        } else {
            goToMainMenu();
        }
    };

    const createLiveViewer = opts.createLiveViewer ?? (async (mountEl: HTMLElement) => {
        const { boot } = await loadBootModule();
        return boot({
            mountEl,
            mode: "live",
            autoStart: false,
        });
    });

    const render = (state: AppState): void => {
        preGameLayer.innerHTML = "";

        if (state.kind === "LIVE_GAME") {
            preGameLayer.style.display = "none";
            liveLayer.style.display = "block";
            void mountLiveGameShell(state.caseId);
            return;
        }

        if (state.kind !== "CONNECTING") {
            cancelPendingLaunch();
        }

        mountRevision += 1;
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
                    onCases: goToCaseSelect,
                }));
                break;
            case "CASE_SELECT":
                preGameLayer.appendChild(
                    renderCaseSelectScreen({
                        cases: PRE_GAME_CASES,
                        onBack: goToMainMenu,
                        onPickCase: beginCaseLaunch,
                    })
                );
                break;
            case "CONNECTING":
                if (state.phase !== "CASE_LAUNCH" && !launchSessionStore.getLatestMetadata()) {
                    stateStore.transition({
                        kind: "ERROR",
                        code: "UNEXPECTED_STATE",
                        message: "Launch metadata is missing; return to case selection and relaunch.",
                        recoverTo: "CASE_SELECT",
                    });
                    return;
                }
                preGameLayer.appendChild(
                    renderConnectingScreen({
                        caseId: state.caseId,
                        phase: state.phase,
                        onBackToCases: goToCaseSelect,
                        onBackToMenu: goToMainMenu,
                    })
                );
                break;
            case "ERROR":
                preGameLayer.appendChild(
                    renderErrorScreen({
                        code: state.code,
                        message: state.message,
                        recoverTo: state.recoverTo,
                        onRecover: () => recoverFromError(state.recoverTo),
                    })
                );
                break;
            default:
                preGameLayer.appendChild(
                    renderErrorScreen({
                        code: "UNEXPECTED_STATE",
                        message: `Unhandled app state: ${(state as { kind: string }).kind}`,
                        recoverTo: "MAIN_MENU",
                        onRecover: goToMainMenu,
                    })
                );
                break;
        }
    };

    const loadBootModule = (): Promise<typeof import("./boot")> => {
        if (!bootModulePromise) {
            bootModulePromise = import("./boot");
        }
        return bootModulePromise;
    };

    const requestCaseLaunch = async (
        caseId: EnqueteurCaseId,
        attemptRevision: number,
        launchRequest: CaseLaunchRequest,
        signal: AbortSignal
    ): Promise<void> => {
        try {
            const metadata = await caseLaunchClient.startCase(launchRequest, { signal });

            if (destroyed || attemptRevision !== launchRevision) return;
            launchSessionStore.markSuccess(metadata);

            const current = stateStore.getState();
            if (current.kind === "CONNECTING" && current.caseId === caseId) {
                stateStore.transition({
                    kind: "CONNECTING",
                    caseId,
                    phase: "SESSION_STARTUP",
                });
            }
        } catch (err: unknown) {
            if (destroyed || attemptRevision !== launchRevision) return;
            if (isAbortError(err)) return;

            const details = describeCaseLaunchError(err);
            launchSessionStore.markFailure({
                request: launchRequest,
                message: details.message,
                code: details.code,
                field: details.field,
                status: details.status,
                occurredAt: new Date().toISOString(),
            });
            stateStore.transition({
                kind: "ERROR",
                code: "LAUNCH_FAILURE",
                message: details.message,
                recoverTo: "CASE_SELECT",
            });
        } finally {
            if (attemptRevision === launchRevision) {
                pendingLaunchAbortController = null;
            }
        }
    };

    const mountLiveGameShell = async (caseId: EnqueteurCaseId): Promise<void> => {
        const activeRevision = ++mountRevision;

        if (viewer) {
            viewer.setVisible(true);
            return;
        }

        if (!viewer) {
            try {
                if (destroyed) return;
                if (activeRevision !== mountRevision) return;

                const nextViewer = await createLiveViewer(liveLayer);
                if (destroyed || activeRevision !== mountRevision) {
                    nextViewer.stop();
                    return;
                }

                viewer = nextViewer;
                viewer.setVisible(stateStore.getState().kind === "LIVE_GAME");
            } catch (err: unknown) {
                if (destroyed) return;
                if (activeRevision !== mountRevision) return;

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
    };

    const unsubscribe = stateStore.subscribe(render);
    beginBootFlow(stateStore, { loadingDurationMs: opts.loadingDurationMs });

    return {
        getState: () => stateStore.getState(),
        getLaunchMetadata: () => launchSessionStore.getLatestMetadata(),
        getLaunchFailure: () => launchSessionStore.getLatestFailure(),
        transition: (next) => stateStore.transition(next),
        destroy: () => {
            destroyed = true;
            cancelPendingLaunch();
            launchSessionStore.clear();
            mountRevision += 1;
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

function isAbortError(err: unknown): boolean {
    if (err instanceof DOMException && err.name === "AbortError") return true;
    if (err instanceof Error && err.name === "AbortError") return true;
    return false;
}

function describeCaseLaunchError(err: unknown): {
    message: string;
    code: string;
    field?: string;
    status?: number;
} {
    if (err instanceof CaseLaunchError) {
        return {
            message: err.field
            ? `Case launch failed (${err.code}, field ${err.field}): ${err.message}`
            : `Case launch failed (${err.code}): ${err.message}`,
            code: err.code,
            field: err.field,
            status: err.status,
        };
    }
    if (err instanceof Error) {
        return {
            message: `Case launch failed: ${err.message}`,
            code: "CASE_LAUNCH_FAILED",
        };
    }
    return {
        message: `Case launch failed: ${String(err)}`,
        code: "CASE_LAUNCH_FAILED",
    };
}
