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
    type KernelHelloPayload,
    type EnqueteurLiveClientLike,
    type EnqueteurLiveProtocolErrorCode,
    type SubscribePayload,
} from "./live/enqueteurLiveClient";

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
type LiveConnectionFailureReason =
    | EnqueteurLiveProtocolErrorCode
    | "TRANSPORT_ERROR"
    | "SOCKET_CLOSED"
    | "SUBSCRIBE_SEND_FAILED"
    | "CONNECT_THROW"
    | string;

type LiveConnectionFailure = {
    reason: LiveConnectionFailureReason;
    message: string;
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

    const caseLaunchClient = opts.caseLaunchClient ?? createCaseLaunchClient();
    const createLiveClient = opts.createLiveClient ?? ((session: LaunchSessionInfo) => (
        new EnqueteurLiveClient({
            url: session.wsUrl,
            expectedEngineName: session.engineName,
            expectedSchemaVersion: session.schemaVersion,
            supportedSchemaVersions: [session.schemaVersion],
        })
    ));

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

    const syncLiveStateToViewer = (): void => {
        if (!viewer) return;
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

        const failLiveConnection = (
            details: LiveConnectionFailure
        ): void => {
            if (!isCurrentAttempt()) return;
            stopLiveConnection();

            const classification = classifyLiveConnectionFailure(details);
            stateStore.transition({
                kind: "ERROR",
                code: classification.code,
                message: details.message,
                recoverTo: classification.recoverTo,
            });
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
                if (stateStore.getState().kind !== "CONNECTING") return;
                failLiveConnection({
                    reason: "SOCKET_CLOSED",
                    message: describeLiveSocketClose(event),
                });
            })
        );
        liveClientUnsubscribers.push(
            client.onTransportError(() => {
                if (!isCurrentAttempt()) return;
                failLiveConnection({
                    reason: "TRANSPORT_ERROR",
                    message: "Live socket transport failed before baseline was ready.",
                });
            })
        );
        liveClientUnsubscribers.push(
            client.onProtocolError((error) => {
                if (!isCurrentAttempt()) return;
                failLiveConnection({
                    reason: error.code,
                    message: `Live protocol error (${error.code}): ${error.message}`,
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
        subscribeToMessage("COMMAND_ACCEPTED", () => {
            if (liveBaselineSnapshot) return;
            failLiveConnection({
                reason: "BAD_SEQUENCE",
                message: "COMMAND_ACCEPTED is not valid during live startup handshake.",
            });
        });
        subscribeToMessage("COMMAND_REJECTED", () => {
            if (liveBaselineSnapshot) return;
            failLiveConnection({
                reason: "BAD_SEQUENCE",
                message: "COMMAND_REJECTED is not valid during live startup handshake.",
            });
        });
        subscribeToMessage("ERROR", (envelope) => {
            failLiveConnection({
                reason: envelope.payload.code,
                message: `Live kernel error (${envelope.payload.code}): ${envelope.payload.message}`,
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

        if (viewer) {
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

function classifyLiveConnectionFailure(details: LiveConnectionFailure): {
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

function describeLiveSocketClose(event: CloseEvent): string {
    const closeCode = Number.isInteger(event.code) ? String(event.code) : "unknown";
    const reason = typeof event.reason === "string" && event.reason.length > 0
        ? event.reason
        : "no reason provided";
    return `Live socket closed before baseline was ready (code ${closeCode}, reason: ${reason}).`;
}
