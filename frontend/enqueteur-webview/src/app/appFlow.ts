import {
    AppStateStore,
    type AppErrorCode,
    type ConnectingPhase,
    type AppRecoverTarget,
    beginBootFlow,
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
} from "./api/caseLaunchClient";
import { LaunchSessionStore, type LaunchFailureRecord } from "./launch/launchSessionStore";
import { getSharedLaunchSessionStore } from "./launch/sharedLaunchSessionStore";
import type { LaunchSessionInfo } from "./launch/launchSessionInfo";
import { renderLoadingScreen } from "./screens/LoadingScreen";
import { renderCaseSelectScreen } from "./screens/CaseSelectScreen";
import { renderConnectingScreen } from "./screens/ConnectingScreen";
import { renderErrorScreen } from "./screens/ErrorScreen";
import { renderMainMenuScreen } from "./screens/MainMenuScreen";
import {
    EnqueteurLiveClient,
    type EnqueteurChannel,
    type EnqueteurInboundEnvelopeByType,
    type FrameDiffPayload,
    type FullSnapshotPayload,
    type InputCommandPayload,
    type KernelHelloPayload,
    type EnqueteurLiveClientLike,
    type EnqueteurLiveProtocolErrorCode,
    type SubscribePayload,
} from "./live/enqueteurLiveClient";
import type { LiveCommandBridge } from "./live/liveCommandBridge";

export type AppFlowOpts = {
    mountEl: HTMLElement;
    loadingDurationMs?: number;
    createLiveViewer?: (mountEl: HTMLElement) => ViewerHandle | Promise<ViewerHandle>;
    caseLaunchClient?: CaseLaunchClient;
    launchSessionStore?: LaunchSessionStore;
    createLiveClient?: (session: LaunchSessionInfo) => EnqueteurLiveClientLike;
};

export type AppFlowHandle = {
    getState: () => AppState;
    getLaunchSession: () => LaunchSessionInfo | null;
    getLaunchMetadata: () => LaunchSessionInfo | null;
    getLaunchFailure: () => LaunchFailureRecord | null;
    transition: (next: AppState) => void;
    destroy: () => void;
};

type ViewerHandle = import("./boot").ViewerHandle;
type BootShellMode = import("./boot").BootShellMode;
type LiveConnectionFailureReason =
    | EnqueteurLiveProtocolErrorCode
    | "TRANSPORT_ERROR"
    | "SOCKET_CLOSED"
    | "SUBSCRIBE_SEND_FAILED"
    | "CONNECT_THROW"
    | string;

type LiveConnectionStage = "STARTUP" | "RUNTIME";

type LiveConnectionFailure = {
    reason: LiveConnectionFailureReason;
    message: string;
    stage?: LiveConnectionStage;
};

type PendingCommandAck = {
    timeoutId: number;
    resolve: (value: { accepted: boolean; reasonCode?: string; message?: string }) => void;
};

const LIVE_SUBSCRIBE_REQUEST: SubscribePayload = {
    stream: "LIVE",
    channels: [
        "WORLD",
        "NPCS",
        "INVESTIGATION",
        "DIALOGUE",
        "LEARNING",
        "EVENTS",
    ],
    diff_policy: "DIFF_ONLY",
    snapshot_policy: "ON_JOIN",
    compression: "NONE",
};
const LIVE_COMMAND_ACK_TIMEOUT_MS = 5_000;

export function mountAppFlow(opts: AppFlowOpts): AppFlowHandle {
    const root = document.createElement("div");
    root.className = "app-flow";

    const preGameLayer = document.createElement("div");
    preGameLayer.className = "app-flow-layer app-flow-layer-pregame";

    const liveLayer = document.createElement("div");
    liveLayer.className = "app-flow-layer app-flow-layer-live";

    const liveActionBar = document.createElement("div");
    liveActionBar.className = "flow-live-actions";
    liveActionBar.style.display = "none";

    const backToCasesBtn = document.createElement("button");
    backToCasesBtn.type = "button";
    backToCasesBtn.className = "flow-action-btn flow-live-action-btn";
    backToCasesBtn.textContent = "Back To Cases";

    const mainMenuBtn = document.createElement("button");
    mainMenuBtn.type = "button";
    mainMenuBtn.className = "flow-action-btn flow-live-action-btn";
    mainMenuBtn.textContent = "Main Menu";

    liveActionBar.append(backToCasesBtn, mainMenuBtn);
    liveLayer.appendChild(liveActionBar);

    root.appendChild(preGameLayer);
    root.appendChild(liveLayer);
    opts.mountEl.appendChild(root);

    const stateStore = new AppStateStore({ kind: "BOOT" });
    const launchSessionStore = opts.launchSessionStore ?? getSharedLaunchSessionStore();
    let viewer: ViewerHandle | null = null;
    let bootModulePromise: Promise<typeof import("./boot")> | null = null;
    let mountRevision = 0;
    let destroyed = false;
    let launchRevision = 0;
    let pendingLaunchAbortController: AbortController | null = null;
    let liveConnectionRevision = 0;
    let liveClient: EnqueteurLiveClientLike | null = null;
    let liveClientUnsubscribers: Array<() => void> = [];
    let liveKernelHello: KernelHelloPayload | null = null;
    let liveBaselineSnapshot: FullSnapshotPayload | null = null;
    let livePendingDiffs: FrameDiffPayload[] = [];
    let liveBaselineIngestedByViewer = false;
    let liveWarningMessage: string | null = null;
    let liveCommandBridge: LiveCommandBridge | null = null;
    const pendingCommandAcks = new Map<string, PendingCommandAck>();

    const caseLaunchClient = opts.caseLaunchClient ?? createCaseLaunchClient();
    const createLiveClient = opts.createLiveClient ?? ((session: LaunchSessionInfo) => (
        new EnqueteurLiveClient({
            url: session.wsUrl,
            expectedEngineName: session.engineName,
            expectedSchemaVersion: session.schemaVersion,
            supportedSchemaVersions: [session.schemaVersion],
        })
    ));

    const setLiveCommandBridge = (bridge: LiveCommandBridge | null): void => {
        liveCommandBridge = bridge;
        viewer?.setLiveCommandBridge?.(bridge);
    };

    const clearPendingCommandAcks = (
        reasonCode: string,
        message: string
    ): void => {
        for (const [clientCmdId, pending] of pendingCommandAcks.entries()) {
            window.clearTimeout(pending.timeoutId);
            pending.resolve({
                accepted: false,
                reasonCode,
                message: `${message} (client_cmd_id=${clientCmdId})`,
            });
        }
        pendingCommandAcks.clear();
    };

    const resolvePendingCommandAck = (
        clientCmdId: string,
        result: { accepted: boolean; reasonCode?: string; message?: string }
    ): void => {
        const pending = pendingCommandAcks.get(clientCmdId);
        if (!pending) return;
        pendingCommandAcks.delete(clientCmdId);
        window.clearTimeout(pending.timeoutId);
        pending.resolve(result);
    };

    const stopLiveConnection = (): void => {
        if (liveClient || liveClientUnsubscribers.length > 0) {
            liveConnectionRevision += 1;
            const clientToDisconnect = liveClient;
            liveClient = null;

            for (const unsubscribe of liveClientUnsubscribers) unsubscribe();
            liveClientUnsubscribers = [];

            try {
                clientToDisconnect?.disconnect();
            } catch {
                // ignore close failures during teardown
            }
        }
        setLiveCommandBridge(null);
        clearPendingCommandAcks(
            "RUNTIME_NOT_READY",
            "Live session is not connected."
        );
        liveWarningMessage = null;
        liveKernelHello = null;
        liveBaselineSnapshot = null;
        livePendingDiffs = [];
        liveBaselineIngestedByViewer = false;
    };

    const cancelPendingLaunch = (): void => {
        launchRevision += 1;
        if (pendingLaunchAbortController) {
            pendingLaunchAbortController.abort();
            pendingLaunchAbortController = null;
        }
        stopLiveConnection();
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
    backToCasesBtn.addEventListener("click", goToCaseSelect);
    mainMenuBtn.addEventListener("click", goToMainMenu);
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

    const retryLaunchFromFailure = (): void => {
        const latestFailure = launchSessionStore.getLatestFailure();
        if (!latestFailure) {
            goToCaseSelect();
            return;
        }
        beginCaseLaunch(latestFailure.request.caseId);
    };

    const retryLiveConnectionFromSession = (): void => {
        const latestSession = launchSessionStore.getLatestSession();
        if (!latestSession) {
            goToCaseSelect();
            return;
        }

        launchRevision += 1;
        if (pendingLaunchAbortController) {
            pendingLaunchAbortController.abort();
            pendingLaunchAbortController = null;
        }
        stopLiveConnection();
        liveWarningMessage = null;

        const attemptRevision = launchRevision;
        stateStore.transition({
            kind: "CONNECTING",
            caseId: latestSession.caseId,
            phase: "SESSION_STARTUP",
        });
        beginLiveConnection(latestSession.caseId, attemptRevision, latestSession);
    };

    const createLiveViewer = opts.createLiveViewer ?? (async (mountEl: HTMLElement) => {
        const { boot } = await loadBootModule();
        const shellMode = resolveShellModeForSession(launchSessionStore.getLatestSession());
        return boot({
            mountEl,
            mode: "live",
            shellMode,
            autoStart: false,
        });
    });

    const syncLiveStateToViewer = (): void => {
        if (!viewer) return;
        viewer.setLiveCommandBridge?.(liveCommandBridge);
        if (liveKernelHello) {
            viewer.ingestLiveKernelHello?.(liveKernelHello);
        }
        if (!liveBaselineSnapshot) return;
        if (!liveBaselineIngestedByViewer) {
            viewer.ingestLiveSnapshot?.(liveBaselineSnapshot);
            liveBaselineIngestedByViewer = true;
        }
        if (livePendingDiffs.length > 0) {
            for (const diff of livePendingDiffs) {
                viewer.ingestLiveFrameDiff?.(diff);
            }
            livePendingDiffs = [];
        }
    };

    const resolveErrorRetry = (state: Extract<AppState, { kind: "ERROR" }>): {
        label: string;
        run: () => void;
    } | null => {
        if (state.code === "LAUNCH_FAILURE" && launchSessionStore.getLatestFailure()) {
            return {
                label: "Retry Launch",
                run: retryLaunchFromFailure,
            };
        }
        if (state.code === "CONNECTION_FAILURE" && launchSessionStore.getLatestSession()) {
            return {
                label: "Retry Connection",
                run: retryLiveConnectionFromSession,
            };
        }
        return null;
    };

    const render = (state: AppState): void => {
        preGameLayer.innerHTML = "";

        if (state.kind === "LIVE_GAME") {
            preGameLayer.style.display = "none";
            liveLayer.style.display = "block";
            const shellMode = resolveShellModeForSession(launchSessionStore.getLatestSession());
            liveActionBar.style.display = shellMode === "demo" ? "none" : "flex";
            void mountLiveGameShell(state.caseId);
            return;
        }

        if (state.kind !== "CONNECTING") {
            cancelPendingLaunch();
        }

        mountRevision += 1;
        preGameLayer.style.display = "flex";
        liveLayer.style.display = "none";
        liveActionBar.style.display = "none";
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
                if (state.phase !== "CASE_LAUNCH" && !launchSessionStore.getLatestSession()) {
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
                        demoPathLabel: getPreGameCaseEntry(state.caseId)?.defaultDemoPath.title,
                        blockedStateHint: getPreGameCaseEntry(state.caseId)?.defaultDemoPath.blockedStateHint,
                        warningMessage: liveWarningMessage ?? undefined,
                        onBackToCases: goToCaseSelect,
                        onBackToMenu: goToMainMenu,
                    })
                );
                break;
            case "ERROR": {
                const retry = resolveErrorRetry(state);
                preGameLayer.appendChild(
                    renderErrorScreen({
                        code: state.code,
                        message: state.message,
                        recoverTo: state.recoverTo,
                        onRetry: retry?.run,
                        retryLabel: retry?.label,
                        onRecover: () => recoverFromError(state.recoverTo),
                    })
                );
                break;
            }
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
            launchSessionStore.markSuccessFromMetadata(metadata);

            const current = stateStore.getState();
            if (current.kind === "CONNECTING" && current.caseId === caseId) {
                transitionConnectingPhase(caseId, "SESSION_STARTUP");
                beginLiveConnection(caseId, attemptRevision, launchSessionStore.getLatestSession());
            }
        } catch (err: unknown) {
            if (destroyed || attemptRevision !== launchRevision) return;
            if (isAbortError(err)) return;

            const details = describeCaseLaunchError(err);
            const appError = classifyCaseLaunchFailure(details);
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
                code: appError.code,
                message: details.message,
                recoverTo: appError.recoverTo,
            });
        } finally {
            if (attemptRevision === launchRevision) {
                pendingLaunchAbortController = null;
            }
        }
    };

    const transitionConnectingPhase = (
        caseId: EnqueteurCaseId,
        phase: ConnectingPhase
    ): void => {
        const current = stateStore.getState();
        if (current.kind !== "CONNECTING" || current.caseId !== caseId) return;
        if (current.phase === phase) return;

        stateStore.transition({
            kind: "CONNECTING",
            caseId,
            phase,
        });
    };

    const createLiveCommandBridgeForConnection = (args: {
        client: EnqueteurLiveClientLike;
        attemptRevision: number;
        connectionRevision: number;
    }): LiveCommandBridge => {
        const { client, attemptRevision, connectionRevision } = args;
        const sendInputCommand = (
            client as unknown as { sendInputCommand?: (payload: InputCommandPayload) => boolean }
        ).sendInputCommand;

        const canSendInputCommand = (): boolean => (
            typeof sendInputCommand === "function"
            && !destroyed
            && attemptRevision === launchRevision
            && connectionRevision === liveConnectionRevision
            && liveClient === client
            && stateStore.getState().kind === "LIVE_GAME"
            && liveBaselineSnapshot !== null
        );

        return {
            canSendInputCommand,
            sendInputCommand: async (cmd, commandOpts = {}) => {
                if (!canSendInputCommand() || typeof sendInputCommand !== "function") {
                    return {
                        accepted: false,
                        clientCmdId: makeClientCmdId(),
                        reasonCode: "RUNTIME_NOT_READY",
                        message: "Live runtime connection is not ready for INPUT_COMMAND dispatch.",
                    };
                }

                const clientCmdId = makeClientCmdId();
                const tickTarget = Math.max(
                    0,
                    Math.floor(commandOpts.tickTarget ?? liveBaselineSnapshot?.tick ?? 0)
                );
                const payload: InputCommandPayload = {
                    client_cmd_id: clientCmdId,
                    tick_target: tickTarget,
                    cmd,
                };

                return new Promise((resolve) => {
                    const timeoutId = window.setTimeout(() => {
                        pendingCommandAcks.delete(clientCmdId);
                        resolve({
                            accepted: false,
                            clientCmdId,
                            reasonCode: "COMMAND_ACK_TIMEOUT",
                            message: "Timed out waiting for COMMAND_ACCEPTED/COMMAND_REJECTED.",
                        });
                    }, LIVE_COMMAND_ACK_TIMEOUT_MS);

                    pendingCommandAcks.set(clientCmdId, {
                        timeoutId,
                        resolve: (result) => {
                            resolve({
                                accepted: result.accepted,
                                clientCmdId,
                                reasonCode: result.reasonCode,
                                message: result.message,
                            });
                        },
                    });

                    const sent = sendInputCommand(payload);
                    if (sent) return;

                    const pending = pendingCommandAcks.get(clientCmdId);
                    if (!pending) return;
                    pendingCommandAcks.delete(clientCmdId);
                    window.clearTimeout(pending.timeoutId);
                    pending.resolve({
                        accepted: false,
                        reasonCode: "RUNTIME_NOT_READY",
                        message: "WebSocket is not open for INPUT_COMMAND dispatch.",
                    });
                });
            },
        };
    };

    const beginLiveConnection = (
        caseId: EnqueteurCaseId,
        attemptRevision: number,
        sessionInfo: LaunchSessionInfo | null
    ): void => {
        if (!sessionInfo) {
            stateStore.transition({
                kind: "ERROR",
                code: "UNEXPECTED_STATE",
                message: "Launch metadata is missing; return to case selection and relaunch.",
                recoverTo: "CASE_SELECT",
            });
            return;
        }

        stopLiveConnection();
        const connectionRevision = ++liveConnectionRevision;
        let client: EnqueteurLiveClientLike;
        try {
            client = createLiveClient(sessionInfo);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : String(err);
            stateStore.transition({
                kind: "ERROR",
                code: "STARTUP_INCOMPATIBILITY",
                message: `Live client startup failed: ${message}`,
                recoverTo: "MAIN_MENU",
            });
            return;
        }
        liveClient = client;

        const isCurrentAttempt = (): boolean =>
            !destroyed &&
            attemptRevision === launchRevision &&
            connectionRevision === liveConnectionRevision &&
            liveClient === client;
        let didValidateKernelHello = false;
        let didValidateSubscribed = false;
        liveWarningMessage = null;

        const currentConnectionStage = (): LiveConnectionStage => (
            liveBaselineSnapshot ? "RUNTIME" : "STARTUP"
        );

        const failLiveConnection = (
            details: LiveConnectionFailure
        ): void => {
            if (!isCurrentAttempt()) return;
            const stage = details.stage ?? currentConnectionStage();
            stopLiveConnection();

            const classification = classifyLiveConnectionFailure(details, stage);
            stateStore.transition({
                kind: "ERROR",
                code: classification.code,
                message: details.message,
                recoverTo: classification.recoverTo,
            });
        };

        const handleKernelWarning = (
            code: string,
            message: string
        ): void => {
            const formatted = `Live warning (${code}): ${message}`;
            const currentState = stateStore.getState();
            if (currentState.kind === "CONNECTING" && currentState.caseId === caseId) {
                liveWarningMessage = formatted;
                stateStore.transition({ ...currentState });
                return;
            }

            const currentSession = launchSessionStore.getLatestSession();
            if (
                currentSession?.mode === "dev"
                || Boolean((import.meta as { env?: { DEV?: boolean } }).env?.DEV)
            ) {
                console.warn(formatted);
            }
        };

        const subscribeToMessage = <T extends keyof EnqueteurInboundEnvelopeByType>(
            msgType: T,
            handler: (envelope: EnqueteurInboundEnvelopeByType[T]) => void
        ): void => {
            liveClientUnsubscribers.push(
                client.onMessage(msgType, (envelope) => {
                    if (!isCurrentAttempt()) return;
                    handler(envelope);
                })
            );
        };

        liveClientUnsubscribers.push(
            client.onOpen(() => {
                if (!isCurrentAttempt()) return;
                transitionConnectingPhase(caseId, "HANDSHAKING");
            })
        );
        liveClientUnsubscribers.push(
            client.onClose((event) => {
                if (!isCurrentAttempt()) return;
                const currentState = stateStore.getState();
                if (currentState.kind !== "CONNECTING" && currentState.kind !== "LIVE_GAME") return;
                failLiveConnection({
                    reason: "SOCKET_CLOSED",
                    message: describeLiveSocketClose(event, currentConnectionStage()),
                    stage: currentConnectionStage(),
                });
            })
        );
        liveClientUnsubscribers.push(
            client.onTransportError(() => {
                if (!isCurrentAttempt()) return;
                failLiveConnection({
                    reason: "TRANSPORT_ERROR",
                    message: currentConnectionStage() === "STARTUP"
                        ? "Live socket transport failed before baseline was ready."
                        : "Live socket transport failed during active session.",
                    stage: currentConnectionStage(),
                });
            })
        );
        liveClientUnsubscribers.push(
            client.onProtocolError((error) => {
                if (!isCurrentAttempt()) return;
                failLiveConnection({
                    reason: error.code,
                    message: `Live protocol error (${error.code}): ${error.message}`,
                    stage: currentConnectionStage(),
                });
            })
        );

        subscribeToMessage("KERNEL_HELLO", (envelope) => {
            const currentSession = launchSessionStore.getLatestSession();
            if (!currentSession) {
                failLiveConnection({
                    reason: "UNEXPECTED_STATE",
                    message: "Launch metadata disappeared before KERNEL_HELLO validation.",
                });
                return;
            }

            const currentState = stateStore.getState();
            if (currentState.kind !== "CONNECTING" || currentState.caseId !== caseId) {
                failLiveConnection({
                    reason: "BAD_SEQUENCE",
                    message: "KERNEL_HELLO arrived outside CONNECTING startup state.",
                });
                return;
            }

            const validationError = validateKernelHelloAgainstLaunch({
                payload: envelope.payload,
                sessionInfo: currentSession,
            });
            if (validationError) {
                failLiveConnection(validationError);
                return;
            }
            didValidateKernelHello = true;
            liveKernelHello = envelope.payload;
            syncLiveStateToViewer();

            const didSendSubscribe = client.sendSubscribe(LIVE_SUBSCRIBE_REQUEST);
            if (didSendSubscribe) return;
            failLiveConnection({
                reason: "SUBSCRIBE_SEND_FAILED",
                message: "Live session opened but SUBSCRIBE could not be sent over the WebSocket.",
            });
        });
        subscribeToMessage("SUBSCRIBED", (envelope) => {
            if (!didValidateKernelHello) {
                failLiveConnection({
                    reason: "BAD_SEQUENCE",
                    message: "SUBSCRIBED arrived before a validated KERNEL_HELLO.",
                });
                return;
            }
            const validationError = validateSubscribedAgainstRequest({
                payload: envelope.payload,
                requested: LIVE_SUBSCRIBE_REQUEST,
            });
            if (validationError) {
                failLiveConnection(validationError);
                return;
            }
            didValidateSubscribed = true;
            transitionConnectingPhase(caseId, "WAITING_FOR_BASELINE");
        });
        subscribeToMessage("FULL_SNAPSHOT", (envelope) => {
            if (!didValidateSubscribed) {
                failLiveConnection({
                    reason: "BAD_SEQUENCE",
                    message: "FULL_SNAPSHOT arrived before a validated SUBSCRIBED acknowledgment.",
                });
                return;
            }
            const currentSession = launchSessionStore.getLatestSession();
            if (!currentSession) {
                failLiveConnection({
                    reason: "UNEXPECTED_STATE",
                    message: "Launch metadata disappeared before FULL_SNAPSHOT validation.",
                });
                return;
            }
            const ingestionError = validateBaselineSnapshot({
                payload: envelope.payload,
                sessionInfo: currentSession,
            });
            if (ingestionError) {
                failLiveConnection(ingestionError);
                return;
            }
            liveBaselineSnapshot = envelope.payload;
            livePendingDiffs = [];
            liveBaselineIngestedByViewer = false;
            setLiveCommandBridge(createLiveCommandBridgeForConnection({
                client,
                attemptRevision,
                connectionRevision,
            }));
            syncLiveStateToViewer();

            const current = stateStore.getState();
            if (current.kind !== "CONNECTING" || current.caseId !== caseId) {
                failLiveConnection({
                    reason: "BAD_SEQUENCE",
                    message: "FULL_SNAPSHOT arrived while app was no longer in CONNECTING state.",
                });
                return;
            }
            stateStore.transition({
                kind: "LIVE_GAME",
                caseId,
            });
        });
        subscribeToMessage("FRAME_DIFF", (envelope) => {
            if (!didValidateSubscribed || !liveBaselineSnapshot) {
                failLiveConnection({
                    reason: "BAD_SEQUENCE",
                    message: "FRAME_DIFF arrived before baseline handoff completed.",
                });
                return;
            }
            if (liveBaselineIngestedByViewer && viewer?.ingestLiveFrameDiff) {
                viewer.ingestLiveFrameDiff(envelope.payload);
                return;
            }
            livePendingDiffs.push(envelope.payload);
        });
        subscribeToMessage("COMMAND_ACCEPTED", (envelope) => {
            if (!liveBaselineSnapshot) {
                failLiveConnection({
                    reason: "BAD_SEQUENCE",
                    message: "COMMAND_ACCEPTED is not valid during live startup handshake.",
                });
                return;
            }
            resolvePendingCommandAck(envelope.payload.client_cmd_id, {
                accepted: true,
            });
        });
        subscribeToMessage("COMMAND_REJECTED", (envelope) => {
            if (!liveBaselineSnapshot) {
                failLiveConnection({
                    reason: "BAD_SEQUENCE",
                    message: "COMMAND_REJECTED is not valid during live startup handshake.",
                });
                return;
            }
            resolvePendingCommandAck(envelope.payload.client_cmd_id, {
                accepted: false,
                reasonCode: envelope.payload.reason_code,
                message: envelope.payload.message,
            });
        });
        subscribeToMessage("WARN", (envelope) => {
            handleKernelWarning(envelope.payload.code, envelope.payload.message);
        });
        subscribeToMessage("ERROR", (envelope) => {
            if (liveBaselineSnapshot && !envelope.payload.fatal) {
                handleKernelWarning(envelope.payload.code, envelope.payload.message);
                return;
            }
            if (liveBaselineSnapshot) {
                clearPendingCommandAcks(
                    envelope.payload.code,
                    envelope.payload.message
                );
            }
            failLiveConnection({
                reason: envelope.payload.code,
                message: `Live kernel error (${envelope.payload.code}): ${envelope.payload.message}`,
                stage: currentConnectionStage(),
            });
        });

        transitionConnectingPhase(caseId, "SESSION_STARTUP");
        try {
            client.connect();
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : String(err);
            failLiveConnection({
                reason: "CONNECT_THROW",
                message: `Live WebSocket connect failed before handshake: ${message}`,
            });
        }
    };

    const mountLiveGameShell = async (caseId: EnqueteurCaseId): Promise<void> => {
        const activeRevision = ++mountRevision;
        const shellMode = resolveShellModeForSession(launchSessionStore.getLatestSession());

        if (viewer) {
            viewer.setShellMode?.(shellMode);
            viewer.setVisible(true);
            syncLiveStateToViewer();
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
                viewer.setShellMode?.(shellMode);
                viewer.setVisible(stateStore.getState().kind === "LIVE_GAME");
                syncLiveStateToViewer();
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
        getLaunchSession: () => launchSessionStore.getLatestSession(),
        getLaunchMetadata: () => launchSessionStore.getLatestSession(),
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

function makeClientCmdId(): string {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }

    const template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx";
    return template.replace(/[xy]/g, (ch) => {
        const rand = Math.floor(Math.random() * 16);
        const nibble = ch === "x" ? rand : ((rand & 0x3) | 0x8);
        return nibble.toString(16);
    });
}

function resolveShellModeForSession(session: LaunchSessionInfo | null): BootShellMode {
    if (session?.mode === "dev") return "dev";
    const override = resolvePresentationOverride();
    if (override === "demo") return "demo";
    if (override === "playtest") return "playtest";
    return "playtest";
}

function resolvePresentationOverride(): "demo" | "playtest" | null {
    const env = (import.meta as { env?: { VITE_ENQUETEUR_PRESENTATION_PROFILE?: string } }).env;
    const envPref = normalizePresentationProfile(env?.VITE_ENQUETEUR_PRESENTATION_PROFILE);
    if (envPref) return envPref;

    if (typeof window === "undefined") return null;
    const params = new URLSearchParams(window.location.search);
    const explicit = normalizePresentationProfile(params.get("presentation"));
    if (explicit) return explicit;
    const demoFlag = params.get("demo");
    if (demoFlag === "1" || demoFlag === "true") return "demo";
    return null;
}

function normalizePresentationProfile(value: unknown): "demo" | "playtest" | null {
    if (value === "demo" || value === "playtest") return value;
    return null;
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

function classifyCaseLaunchFailure(details: {
    code: string;
    status?: number;
}): {
    code: AppErrorCode;
    recoverTo: AppRecoverTarget;
} {
    if (details.code === "INVALID_RESPONSE") {
        return {
            code: "STARTUP_INCOMPATIBILITY",
            recoverTo: "MAIN_MENU",
        };
    }
    return {
        code: "LAUNCH_FAILURE",
        recoverTo: "CASE_SELECT",
    };
}

function validateKernelHelloAgainstLaunch(args: {
    payload: EnqueteurInboundEnvelopeByType["KERNEL_HELLO"]["payload"];
    sessionInfo: LaunchSessionInfo;
}): LiveConnectionFailure | null {
    const { payload, sessionInfo } = args;
    if (payload.engine_name !== sessionInfo.engineName) {
        return {
            reason: "UNEXPECTED_KERNEL_IDENTITY",
            message: (
                `KERNEL_HELLO engine mismatch: expected '${sessionInfo.engineName}', `
                + `got '${payload.engine_name}'.`
            ),
        };
    }
    if (payload.schema_version !== sessionInfo.schemaVersion) {
        return {
            reason: "UNEXPECTED_KERNEL_IDENTITY",
            message: (
                `KERNEL_HELLO schema mismatch: expected '${sessionInfo.schemaVersion}', `
                + `got '${payload.schema_version}'.`
            ),
        };
    }
    if (payload.run_id !== sessionInfo.runId) {
        return {
            reason: "KERNEL_HELLO_RUN_MISMATCH",
            message: `KERNEL_HELLO run_id mismatch: expected '${sessionInfo.runId}', got '${payload.run_id}'.`,
        };
    }
    if (payload.world_id !== sessionInfo.worldId) {
        return {
            reason: "KERNEL_HELLO_WORLD_MISMATCH",
            message: `KERNEL_HELLO world_id mismatch: expected '${sessionInfo.worldId}', got '${payload.world_id}'.`,
        };
    }
    return null;
}

function validateSubscribedAgainstRequest(args: {
    payload: EnqueteurInboundEnvelopeByType["SUBSCRIBED"]["payload"];
    requested: SubscribePayload;
}): LiveConnectionFailure | null {
    const { payload, requested } = args;
    if (payload.effective_stream !== "LIVE") {
        return {
            reason: "INVALID_SUBSCRIPTION_ACK",
            message: `SUBSCRIBED effective_stream must be LIVE, got '${payload.effective_stream}'.`,
        };
    }

    const effectiveChannels = payload.effective_channels;
    if (effectiveChannels.length === 0) {
        return {
            reason: "INVALID_SUBSCRIPTION_ACK",
            message: "SUBSCRIBED effective_channels must be non-empty.",
        };
    }

    if (new Set(effectiveChannels).size !== effectiveChannels.length) {
        return {
            reason: "INVALID_SUBSCRIPTION_ACK",
            message: "SUBSCRIBED effective_channels contains duplicates.",
        };
    }

    const requestedChannels = new Set<EnqueteurChannel>(requested.channels);
    const unexpectedChannels = effectiveChannels.filter((channel) => !requestedChannels.has(channel));
    if (unexpectedChannels.length > 0) {
        return {
            reason: "INVALID_SUBSCRIPTION_ACK",
            message: (
                `SUBSCRIBED includes unexpected channels: ${unexpectedChannels.join(", ")}.`
            ),
        };
    }

    if (payload.effective_diff_policy !== requested.diff_policy) {
        return {
            reason: "INVALID_SUBSCRIPTION_ACK",
            message: (
                `SUBSCRIBED diff policy mismatch: expected '${requested.diff_policy}', `
                + `got '${payload.effective_diff_policy}'.`
            ),
        };
    }
    if (payload.effective_snapshot_policy !== requested.snapshot_policy) {
        return {
            reason: "INVALID_SUBSCRIPTION_ACK",
            message: (
                `SUBSCRIBED snapshot policy mismatch: expected '${requested.snapshot_policy}', `
                + `got '${payload.effective_snapshot_policy}'.`
            ),
        };
    }
    if (payload.effective_compression !== requested.compression) {
        return {
            reason: "INVALID_SUBSCRIPTION_ACK",
            message: (
                `SUBSCRIBED compression mismatch: expected '${requested.compression}', `
                + `got '${payload.effective_compression}'.`
            ),
        };
    }

    return null;
}

function validateBaselineSnapshot(args: {
    payload: EnqueteurInboundEnvelopeByType["FULL_SNAPSHOT"]["payload"];
    sessionInfo: LaunchSessionInfo;
}): LiveConnectionFailure | null {
    const { payload, sessionInfo } = args;
    if (payload.schema_version !== sessionInfo.schemaVersion) {
        return {
            reason: "INVALID_BASELINE",
            message: (
                `FULL_SNAPSHOT schema mismatch: expected '${sessionInfo.schemaVersion}', `
                + `got '${payload.schema_version}'.`
            ),
        };
    }

    const visibleRoots = [
        payload.state.world,
        payload.state.npcs,
        payload.state.investigation,
        payload.state.dialogue,
        payload.state.learning,
        payload.state.resolution,
    ];
    if (visibleRoots.every((root) => root === undefined)) {
        return {
            reason: "INVALID_BASELINE",
            message: "FULL_SNAPSHOT.state is missing all Enqueteur visible roots.",
        };
    }

    return null;
}

function classifyLiveConnectionFailure(
    details: LiveConnectionFailure,
    stage: LiveConnectionStage
): {
    code: AppErrorCode;
    recoverTo: AppRecoverTarget;
} {
    if (
        details.reason === "UNEXPECTED_KERNEL_IDENTITY" ||
        details.reason === "UNSUPPORTED_KVP_VERSION" ||
        details.reason === "INVALID_PAYLOAD" ||
        details.reason === "SCHEMA_MISMATCH" ||
        details.reason === "PROTOCOL_VIOLATION" ||
        details.reason === "INVALID_ENVELOPE" ||
        details.reason === "INVALID_JSON" ||
        details.reason === "NON_TEXT_FRAME" ||
        details.reason === "UNKNOWN_MSG_TYPE" ||
        details.reason === "BAD_SEQUENCE" ||
        details.reason === "INVALID_SUBSCRIPTION_ACK" ||
        details.reason === "INVALID_BASELINE" ||
        details.reason === "KERNEL_HELLO_RUN_MISMATCH" ||
        details.reason === "KERNEL_HELLO_WORLD_MISMATCH"
    ) {
        if (stage === "RUNTIME") {
            return {
                code: "CONNECTION_FAILURE",
                recoverTo: "CASE_SELECT",
            };
        }
        return {
            code: "STARTUP_INCOMPATIBILITY",
            recoverTo: "MAIN_MENU",
        };
    }
    return {
        code: "CONNECTION_FAILURE",
        recoverTo: "CASE_SELECT",
    };
}

function describeLiveSocketClose(event: CloseEvent, stage: LiveConnectionStage): string {
    const closeCode = Number.isInteger(event.code) ? String(event.code) : "unknown";
    const reason = typeof event.reason === "string" && event.reason.length > 0
        ? event.reason
        : "no reason provided";
    if (stage === "RUNTIME") {
        return `Live session disconnected (code ${closeCode}, reason: ${reason}).`;
    }
    return `Live socket closed before baseline was ready (code ${closeCode}, reason: ${reason}).`;
}
