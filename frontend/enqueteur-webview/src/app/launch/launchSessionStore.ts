import type { CaseLaunchMetadata } from "../api/caseLaunchClient";

export class LaunchSessionStore {
    private latest: CaseLaunchMetadata | null = null;

    set(metadata: CaseLaunchMetadata): void {
        this.latest = metadata;
    }

    getLatest(): CaseLaunchMetadata | null {
        return this.latest;
    }

    clear(): void {
        this.latest = null;
    }
}
