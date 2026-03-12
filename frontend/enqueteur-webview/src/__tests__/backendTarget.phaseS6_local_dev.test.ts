import { describe, expect, it } from "vitest";

import { resolveBackendApiBaseUrl } from "../app/api/backendTarget";

describe("Phase S6 backend target resolution", () => {
    it("prefers explicit configured API base", () => {
        const resolved = resolveBackendApiBaseUrl({
            configuredBaseUrl: "http://localhost:9000",
            env: {
                DEV: true,
                VITE_ENQUETEUR_API_BASE_URL: "http://localhost:7777",
            },
            location: {
                protocol: "http:",
                hostname: "127.0.0.1",
            },
        });

        expect(resolved).toBe("http://localhost:9000");
    });

    it("uses env API base when explicit value is absent", () => {
        const resolved = resolveBackendApiBaseUrl({
            env: {
                DEV: true,
                VITE_ENQUETEUR_API_BASE_URL: "http://localhost:7777",
            },
            location: {
                protocol: "http:",
                hostname: "127.0.0.1",
            },
        });

        expect(resolved).toBe("http://localhost:7777");
    });

    it("defaults local-dev API base to port 7777 when running in dev", () => {
        const resolved = resolveBackendApiBaseUrl({
            env: {
                DEV: true,
            },
            location: {
                protocol: "http:",
                hostname: "localhost",
            },
        });

        expect(resolved).toBe("http://localhost:7777");
    });

    it("falls back to empty base outside dev when no value is configured", () => {
        const resolved = resolveBackendApiBaseUrl({
            env: {
                DEV: false,
            },
            location: {
                protocol: "http:",
                hostname: "localhost",
            },
        });

        expect(resolved).toBe("");
    });
});
