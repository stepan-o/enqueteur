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
        });

        expect(resolved).toBe("http://localhost:9000");
    });

    it("uses env API base when explicit value is absent", () => {
        const resolved = resolveBackendApiBaseUrl({
            env: {
                DEV: true,
                VITE_ENQUETEUR_API_BASE_URL: "http://localhost:7777",
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
        });

        expect(resolved).toBe("http://127.0.0.1:7777");
    });

    it("uses canonical local backend origin in dev when no explicit base is set", () => {
        const resolved = resolveBackendApiBaseUrl({
            env: {
                DEV: true,
            },
        });

        expect(resolved).toBe("http://127.0.0.1:7777");
    });

    it("falls back to empty base outside dev when no value is configured", () => {
        const resolved = resolveBackendApiBaseUrl({
            env: {
                DEV: false,
            },
        });

        expect(resolved).toBe("");
    });
});
