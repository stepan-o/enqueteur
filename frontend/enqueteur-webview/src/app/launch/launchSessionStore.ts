import type {
    CaseLaunchMetadata,
    CaseLaunchRequest,
} from "../api/caseLaunchClient";

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
    private latestMetadata: CaseLaunchMetadata | null = null;
    private latestFailure: LaunchFailureRecord | null = null;

    begin(request: CaseLaunchRequest): void {
        this.activeRequest = request;
        this.latestMetadata = null;
    }

    markSuccess(metadata: CaseLaunchMetadata): void {
        this.activeRequest = null;
        this.latestFailure = null;
        this.latestMetadata = metadata;
    }

    markFailure(record: LaunchFailureRecord): void {
        this.activeRequest = null;
        this.latestMetadata = null;
        this.latestFailure = record;
    }

    clearProgress(): void {
        this.activeRequest = null;
        this.latestMetadata = null;
    }

    getLatestMetadata(): CaseLaunchMetadata | null {
        return this.latestMetadata;
    }

    getLatestFailure(): LaunchFailureRecord | null {
        return this.latestFailure;
    }

    getActiveRequest(): CaseLaunchRequest | null {
        return this.activeRequest;
    }

    clear(): void {
        this.activeRequest = null;
        this.latestMetadata = null;
        this.latestFailure = null;
    }
}
