import type { EnqueteurCaseId } from "../appState";
import { resolveRuntimeMessage } from "../runtimeMessage";
import { resolveBackendApiBaseUrl } from "./backendTarget";

export type CaseLaunchDifficultyProfile = "D0" | "D1";
export type CaseLaunchMode = "playtest" | "dev";
export const ENQUETEUR_ENGINE_NAME = "enqueteur";
export const ENQUETEUR_SCHEMA_VERSION = "enqueteur_mbam_1";

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
    readonly messageKey?: string;
    readonly messageParams?: Record<string, unknown>;

    constructor(
        message: string,
        opts: {
            status: number;
            code?: string;
            field?: string;
            messageKey?: string;
            messageParams?: Record<string, unknown>;
        }
    ) {
        super(message);
        this.name = "CaseLaunchError";
        this.status = opts.status;
        this.code = opts.code ?? "CASE_LAUNCH_FAILED";
        this.field = opts.field;
        this.messageKey = opts.messageKey;
        this.messageParams = opts.messageParams;
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
            let response: Response;
            try {
                response = await fetchImpl(endpoint, {
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
            } catch (err: unknown) {
                if (isAbortError(err)) {
                    throw err;
                }
                throw new CaseLaunchError(
                    `Could not reach backend launch endpoint at ${endpoint}.`,
                    {
                        status: 503,
                        code: "BACKEND_UNREACHABLE",
                    }
                );
            }

            const payload = await parseJsonPayload(response);
            if (!response.ok) {
                const error = asObject(payload.error);
                const code = asString(error.code) ?? "CASE_LAUNCH_FAILED";
                const field = asString(error.field) ?? undefined;
                const messageKey = asString(error.message_key) ?? undefined;
                const messageParams = asObjectOrNull(error.message_params) ?? undefined;
                const message = resolveRuntimeMessage({
                    message: asString(error.message) ?? `Case launch failed with status ${response.status}.`,
                    messageKey,
                    messageParams,
                    fallbackMessage: `Case launch failed with status ${response.status}.`,
                });
                throw new CaseLaunchError(message, {
                    status: response.status,
                    code,
                    field,
                    messageKey,
                    messageParams,
                });
            }

            return parseCaseLaunchMetadata(payload);
        },
    };
}

function resolveApiBaseUrl(configuredBaseUrl?: string): string {
    return resolveBackendApiBaseUrl({
        configuredBaseUrl,
    });
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
    const engineName = requireExactString(payload.engine_name, "engine_name", ENQUETEUR_ENGINE_NAME);
    const schemaVersion = requireExactString(payload.schema_version, "schema_version", ENQUETEUR_SCHEMA_VERSION);
    const wsUrl = requireWsUrl(payload.ws_url);
    const startedAt = requireTimestamp(payload.started_at, "started_at");
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
        engineName,
        schemaVersion,
        wsUrl,
        startedAt,
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

function requireExactString(value: unknown, field: string, expected: string): string {
    const parsed = requireString(value, field);
    if (parsed !== expected) {
        throw invalidResponse(`Expected '${field}' to be '${expected}' in case launch response.`);
    }
    return parsed;
}

function requireWsUrl(value: unknown): string {
    const parsed = requireString(value, "ws_url");
    try {
        const url = new URL(parsed);
        if (url.protocol !== "ws:" && url.protocol !== "wss:") {
            throw invalidResponse("Missing or invalid 'ws_url' in case launch response.");
        }
    } catch {
        throw invalidResponse("Missing or invalid 'ws_url' in case launch response.");
    }
    return parsed;
}

function requireTimestamp(value: unknown, field: string): string {
    const parsed = requireString(value, field);
    if (!Number.isFinite(Date.parse(parsed))) {
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

function isAbortError(err: unknown): boolean {
    if (err instanceof DOMException && err.name === "AbortError") return true;
    if (err instanceof Error && err.name === "AbortError") return true;
    return false;
}

function asObject(value: unknown): Record<string, unknown> {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        return {};
    }
    return value as Record<string, unknown>;
}

function asObjectOrNull(value: unknown): Record<string, unknown> | null {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        return null;
    }
    return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
    return typeof value === "string" && value.length > 0 ? value : null;
}
