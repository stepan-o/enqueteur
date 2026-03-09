import type {
    CaseLaunchMetadata,
    CaseLaunchRequest,
} from "../api/caseLaunchClient";
import { toLaunchSessionInfo, type LaunchSessionInfo } from "./launchSessionInfo";

export type LaunchFailureRecord = {
    request: CaseLaunchRequest;
    message: string;
    code: string;
    field?: string;
    status?: number;
    occurredAt: string;
};

export class LaunchSessionStore {
    private activeRequest: CaseLaunchRequest | null = null;
    private latestSession: LaunchSessionInfo | null = null;
    private latestFailure: LaunchFailureRecord | null = null;

    begin(request: CaseLaunchRequest): void {
        this.activeRequest = request;
        this.latestSession = null;
    }

    markSuccess(metadata: LaunchSessionInfo): void {
        this.activeRequest = null;
        this.latestFailure = null;
        this.latestSession = metadata;
    }

    markSuccessFromMetadata(metadata: CaseLaunchMetadata): void {
        this.markSuccess(toLaunchSessionInfo(metadata));
    }

    markFailure(record: LaunchFailureRecord): void {
        this.activeRequest = null;
        this.latestSession = null;
        this.latestFailure = record;
    }

    clearProgress(): void {
        this.activeRequest = null;
        this.latestSession = null;
    }

    getLatestSession(): LaunchSessionInfo | null {
        return this.latestSession;
    }

    getLatestFailure(): LaunchFailureRecord | null {
        return this.latestFailure;
    }

    getActiveRequest(): CaseLaunchRequest | null {
        return this.activeRequest;
    }

    clear(): void {
        this.activeRequest = null;
        this.latestSession = null;
        this.latestFailure = null;
    }
}
