export type EnqueteurCaseId = "MBAM_01";

export type ConnectingPhase = "CASE_LAUNCH" | "SESSION_STARTUP" | "WAITING_FOR_BASELINE";

export type AppErrorCode =
    | "LAUNCH_FAILURE"
    | "CONNECTION_FAILURE"
    | "STARTUP_INCOMPATIBILITY"
    | "UNEXPECTED_STATE";

export type AppRecoverTarget = "MAIN_MENU" | "CASE_SELECT";

export type AppState =
    | { kind: "BOOT" }
    | { kind: "LOADING" }
    | { kind: "MAIN_MENU" }
    | { kind: "CASE_SELECT" }
    | { kind: "CONNECTING"; caseId: EnqueteurCaseId; phase: ConnectingPhase }
    | { kind: "LIVE_GAME"; caseId: EnqueteurCaseId }
    | { kind: "ERROR"; code: AppErrorCode; message: string; recoverTo?: AppRecoverTarget };

export type AppStateKind = AppState["kind"];

export type AppStateSubscriber = (state: AppState) => void;

export class AppStateStore {
    private state: AppState;
    private readonly subscribers = new Set<AppStateSubscriber>();

    constructor(initialState: AppState = { kind: "BOOT" }) {
        this.state = initialState;
    }

    getState(): AppState {
        return this.state;
    }

    transition(next: AppState): void {
        this.state = next;
        this.emit();
    }

    subscribe(cb: AppStateSubscriber): () => void {
        this.subscribers.add(cb);
        cb(this.state);
        return () => {
            this.subscribers.delete(cb);
        };
    }

    private emit(): void {
        for (const cb of this.subscribers) cb(this.state);
    }
}

export function beginBootFlow(
    store: AppStateStore,
    opts: { loadingDurationMs?: number } = {}
): void {
    const loadingDurationMs = Math.max(120, Math.floor(opts.loadingDurationMs ?? 420));

    store.transition({ kind: "BOOT" });

    requestAnimationFrame(() => {
        store.transition({ kind: "LOADING" });
        window.setTimeout(() => {
            if (store.getState().kind !== "LOADING") return;
            store.transition({ kind: "MAIN_MENU" });
        }, loadingDurationMs);
    });
}
