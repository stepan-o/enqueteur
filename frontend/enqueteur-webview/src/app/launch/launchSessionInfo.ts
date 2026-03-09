import type { CaseLaunchMetadata } from "../api/caseLaunchClient";

export type LaunchSessionInfo = {
    caseId: CaseLaunchMetadata["caseId"];
    runId: CaseLaunchMetadata["runId"];
    worldId: CaseLaunchMetadata["worldId"];
    engineName: CaseLaunchMetadata["engineName"];
    schemaVersion: CaseLaunchMetadata["schemaVersion"];
    wsUrl: CaseLaunchMetadata["wsUrl"];
    seed: CaseLaunchMetadata["seed"];
    resolvedSeedId: CaseLaunchMetadata["resolvedSeedId"];
    difficultyProfile: CaseLaunchMetadata["difficultyProfile"];
    mode: CaseLaunchMetadata["mode"];
    startedAt: CaseLaunchMetadata["startedAt"];
};

export function toLaunchSessionInfo(metadata: CaseLaunchMetadata): LaunchSessionInfo {
    return {
        caseId: metadata.caseId,
        runId: metadata.runId,
        worldId: metadata.worldId,
        engineName: metadata.engineName,
        schemaVersion: metadata.schemaVersion,
        wsUrl: metadata.wsUrl,
        seed: metadata.seed,
        resolvedSeedId: metadata.resolvedSeedId,
        difficultyProfile: metadata.difficultyProfile,
        mode: metadata.mode,
        startedAt: metadata.startedAt,
    };
}
