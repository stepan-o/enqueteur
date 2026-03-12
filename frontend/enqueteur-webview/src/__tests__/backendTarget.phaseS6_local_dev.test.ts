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

    it("treats blank env API base as unset and falls back to canonical local target", () => {
        const resolved = resolveBackendApiBaseUrl({
            env: {
                DEV: true,
                VITE_ENQUETEUR_API_BASE_URL: "   ",
            },
            location: {
                protocol: "http:",
                hostname: "localhost",
            },
        });

        expect(resolved).toBe("http://127.0.0.1:7777");
    });

    it("defaults local-dev API base to canonical backend origin in dev", () => {
        const resolved = resolveBackendApiBaseUrl({
            env: {
                DEV: true,
            },
            location: {
                protocol: "http:",
                hostname: "localhost",
            },
        });

        expect(resolved).toBe("http://127.0.0.1:7777");
    });

    it("keeps canonical local backend origin regardless of frontend location host/protocol", () => {
        const fromHttpsLocalhost = resolveBackendApiBaseUrl({
            env: {
                DEV: true,
            },
            location: {
                protocol: "https:",
                hostname: "localhost",
            },
        });
        const fromHttpLan = resolveBackendApiBaseUrl({
            env: {
                DEV: true,
            },
            location: {
                protocol: "http:",
                hostname: "192.168.1.42",
            },
        });

        expect(fromHttpsLocalhost).toBe("http://127.0.0.1:7777");
        expect(fromHttpLan).toBe("http://127.0.0.1:7777");
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
