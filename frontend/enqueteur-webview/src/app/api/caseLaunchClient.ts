import type { EnqueteurCaseId } from "../appState";

export type CaseLaunchDifficultyProfile = "D0" | "D1";
export type CaseLaunchMode = "playtest" | "dev";

export type CaseLaunchRequest = {
    caseId: EnqueteurCaseId;
    seed: string | number;
    difficultyProfile: CaseLaunchDifficultyProfile;
    mode: CaseLaunchMode;
};

export type CaseLaunchMetadata = {
    runId: string;
    worldId: string;
    caseId: EnqueteurCaseId;
    seed: string | number;
    resolvedSeedId: string;
    difficultyProfile: CaseLaunchDifficultyProfile;
    mode: CaseLaunchMode;
    engineName: string;
    schemaVersion: string;
    wsUrl: string;
    startedAt: string;
};

export type CaseLaunchClient = {
    startCase: (req: CaseLaunchRequest, opts?: { signal?: AbortSignal }) => Promise<CaseLaunchMetadata>;
};

export class CaseLaunchError extends Error {
    readonly status: number;
    readonly code: string;
    readonly field?: string;

    constructor(message: string, opts: { status: number; code?: string; field?: string }) {
        super(message);
        this.name = "CaseLaunchError";
        this.status = opts.status;
        this.code = opts.code ?? "CASE_LAUNCH_FAILED";
        this.field = opts.field;
    }
}

type CreateCaseLaunchClientOpts = {
    apiBaseUrl?: string;
    fetchImpl?: typeof fetch;
};

export function createCaseLaunchClient(opts: CreateCaseLaunchClientOpts = {}): CaseLaunchClient {
    const fetchImpl = opts.fetchImpl ?? fetch;
    const apiBaseUrl = resolveApiBaseUrl(opts.apiBaseUrl);
    const endpoint = joinApiPath(apiBaseUrl, "/api/cases/start");

    return {
        startCase: async (req, startOpts = {}) => {
            const response = await fetchImpl(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    case_id: req.caseId,
                    seed: req.seed,
                    difficulty_profile: req.difficultyProfile,
                    mode: req.mode,
                }),
                signal: startOpts.signal,
            });

            const payload = await parseJsonPayload(response);
            if (!response.ok) {
                const error = asObject(payload.error);
                const message = asString(error.message) ?? `Case launch failed with status ${response.status}.`;
                throw new CaseLaunchError(message, {
                    status: response.status,
                    code: asString(error.code) ?? "CASE_LAUNCH_FAILED",
                    field: asString(error.field) ?? undefined,
                });
            }

            return parseCaseLaunchMetadata(payload);
        },
    };
}

function resolveApiBaseUrl(configuredBaseUrl?: string): string {
    if (configuredBaseUrl && configuredBaseUrl.trim()) {
        return configuredBaseUrl.trim();
    }
    const env = (import.meta as { env?: { VITE_ENQUETEUR_API_BASE_URL?: string } }).env;
    const envValue = (env?.VITE_ENQUETEUR_API_BASE_URL ?? "").trim();
    return envValue;
}

function joinApiPath(baseUrl: string, path: string): string {
    const base = baseUrl.trim();
    if (!base) return path;
    return `${base.replace(/\/+$/, "")}${path}`;
}

async function parseJsonPayload(response: Response): Promise<Record<string, unknown>> {
    try {
        const payload = (await response.json()) as unknown;
        return asObject(payload);
    } catch {
        throw new CaseLaunchError("Case launch response was not valid JSON.", {
            status: response.status,
            code: "INVALID_RESPONSE",
        });
    }
}

function parseCaseLaunchMetadata(payload: Record<string, unknown>): CaseLaunchMetadata {
    const caseId = requireCaseId(payload.case_id);
    const difficultyProfile = requireDifficultyProfile(payload.difficulty_profile);
    const mode = requireMode(payload.mode);
    const seed = payload.seed;
    if (!isSeed(seed)) {
        throw invalidResponse("Missing or invalid 'seed' in case launch response.");
    }

    return {
        runId: requireString(payload.run_id, "run_id"),
        worldId: requireString(payload.world_id, "world_id"),
        caseId,
        seed,
        resolvedSeedId: requireString(payload.resolved_seed_id, "resolved_seed_id"),
        difficultyProfile,
        mode,
        engineName: requireString(payload.engine_name, "engine_name"),
        schemaVersion: requireString(payload.schema_version, "schema_version"),
        wsUrl: requireString(payload.ws_url, "ws_url"),
        startedAt: requireString(payload.started_at, "started_at"),
    };
}

function requireCaseId(value: unknown): EnqueteurCaseId {
    if (value === "MBAM_01") return value;
    throw invalidResponse("Missing or invalid 'case_id' in case launch response.");
}

function requireDifficultyProfile(value: unknown): CaseLaunchDifficultyProfile {
    if (value === "D0" || value === "D1") return value;
    throw invalidResponse("Missing or invalid 'difficulty_profile' in case launch response.");
}

function requireMode(value: unknown): CaseLaunchMode {
    if (value === "playtest" || value === "dev") return value;
    throw invalidResponse("Missing or invalid 'mode' in case launch response.");
}

function requireString(value: unknown, field: string): string {
    const parsed = asString(value);
    if (!parsed) {
        throw invalidResponse(`Missing or invalid '${field}' in case launch response.`);
    }
    return parsed;
}

function invalidResponse(message: string): CaseLaunchError {
    return new CaseLaunchError(message, {
        status: 502,
        code: "INVALID_RESPONSE",
    });
}

function isSeed(value: unknown): value is string | number {
    return typeof value === "string" || typeof value === "number";
}

function asObject(value: unknown): Record<string, unknown> {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        return {};
    }
    return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
    return typeof value === "string" && value.length > 0 ? value : null;
}
