const DEFAULT_LOCAL_BACKEND_HOST = "127.0.0.1";
const DEFAULT_LOCAL_BACKEND_PORT = 7777;

type BackendTargetEnv = {
    VITE_ENQUETEUR_API_BASE_URL?: string;
    DEV?: boolean;
};

type BackendTargetLocation = {
    protocol?: string;
    hostname?: string;
} | null;

type ResolveBackendApiBaseUrlOpts = {
    configuredBaseUrl?: string;
    env?: BackendTargetEnv;
    location?: BackendTargetLocation;
};

export function resolveBackendApiBaseUrl(opts: ResolveBackendApiBaseUrlOpts = {}): string {
    const configuredBaseUrl = normalize(opts.configuredBaseUrl);
    if (configuredBaseUrl) {
        return configuredBaseUrl;
    }

    const env = opts.env ?? readImportMetaEnv();
    const envBaseUrl = normalize(env?.VITE_ENQUETEUR_API_BASE_URL);
    if (envBaseUrl) {
        return envBaseUrl;
    }

    if (!isDevMode(env)) {
        return "";
    }

    return buildLocalBackendOrigin(opts.location ?? readGlobalLocation());
}

function isDevMode(env: BackendTargetEnv | undefined): boolean {
    return Boolean(env?.DEV);
}

function buildLocalBackendOrigin(location: BackendTargetLocation): string {
    const protocol = location?.protocol === "https:" ? "https:" : "http:";
    const hostname = normalize(location?.hostname) ?? DEFAULT_LOCAL_BACKEND_HOST;
    return `${protocol}//${hostname}:${DEFAULT_LOCAL_BACKEND_PORT}`;
}

function readImportMetaEnv(): BackendTargetEnv | undefined {
    return (import.meta as { env?: BackendTargetEnv }).env;
}

function readGlobalLocation(): BackendTargetLocation {
    const value = (globalThis as { location?: { protocol?: string; hostname?: string } }).location;
    if (!value) {
        return null;
    }
    return {
        protocol: value.protocol,
        hostname: value.hostname,
    };
}

function normalize(value: unknown): string {
    return typeof value === "string" ? value.trim() : "";
}
