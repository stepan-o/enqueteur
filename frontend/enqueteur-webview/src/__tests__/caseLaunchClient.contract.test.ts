import { describe, expect, it, vi } from "vitest";

import {
    CaseLaunchError,
    ENQUETEUR_ENGINE_NAME,
    ENQUETEUR_SCHEMA_VERSION,
    createCaseLaunchClient,
} from "../app/api/caseLaunchClient";

const VALID_RESPONSE = {
    run_id: "run-123",
    world_id: "world-123",
    case_id: "MBAM_01",
    seed: "A",
    resolved_seed_id: "A",
    difficulty_profile: "D0",
    mode: "playtest",
    engine_name: ENQUETEUR_ENGINE_NAME,
    schema_version: ENQUETEUR_SCHEMA_VERSION,
    ws_url: "ws://localhost:7777/live?run_id=run-123",
    started_at: "2026-03-09T10:00:00Z",
};

describe("case launch client contract hardening", () => {
    it("parses a valid deterministic MBAM launch response", async () => {
        const fetchImpl = vi.fn(async () =>
            new Response(JSON.stringify(VALID_RESPONSE), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            })
        );
        const client = createCaseLaunchClient({ fetchImpl });

        const metadata = await client.startCase({
            caseId: "MBAM_01",
            seed: "A",
            difficultyProfile: "D0",
            mode: "playtest",
        });

        expect(metadata.engineName).toBe(ENQUETEUR_ENGINE_NAME);
        expect(metadata.schemaVersion).toBe(ENQUETEUR_SCHEMA_VERSION);
        expect(metadata.wsUrl).toBe("ws://localhost:7777/live?run_id=run-123");
    });

    it("rejects responses with unexpected engine/schema contract values", async () => {
        const fetchImpl = vi.fn(async () =>
            new Response(
                JSON.stringify({
                    ...VALID_RESPONSE,
                    schema_version: "other_schema",
                }),
                {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                }
            )
        );
        const client = createCaseLaunchClient({ fetchImpl });

        await expect(
            client.startCase({
                caseId: "MBAM_01",
                seed: "A",
                difficultyProfile: "D0",
                mode: "playtest",
            })
        ).rejects.toEqual(
            expect.objectContaining<Partial<CaseLaunchError>>({
                code: "INVALID_RESPONSE",
                status: 502,
            })
        );
    });

    it("rejects responses with invalid websocket targets", async () => {
        const fetchImpl = vi.fn(async () =>
            new Response(
                JSON.stringify({
                    ...VALID_RESPONSE,
                    ws_url: "http://localhost:7777/live?run_id=run-123",
                }),
                {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                }
            )
        );
        const client = createCaseLaunchClient({ fetchImpl });

        await expect(
            client.startCase({
                caseId: "MBAM_01",
                seed: "A",
                difficultyProfile: "D0",
                mode: "playtest",
            })
        ).rejects.toEqual(
            expect.objectContaining<Partial<CaseLaunchError>>({
                code: "INVALID_RESPONSE",
                status: 502,
            })
        );
    });
});
