import { describe, expect, it } from "vitest";

import { resolveMbamSeedRunBases } from "../app/mbamReplaySeeds";

describe("Phase 7 replay seed run base resolution", () => {
    it("falls back to shared offline base when per-seed env values are absent", () => {
        const bases = resolveMbamSeedRunBases({}, "/demo/kvp_demo_1min");
        expect(bases).toEqual({
            A: "/demo/kvp_demo_1min",
            B: "/demo/kvp_demo_1min",
            C: "/demo/kvp_demo_1min",
        });
    });

    it("uses explicit per-seed env values when provided", () => {
        const bases = resolveMbamSeedRunBases(
            {
                VITE_WEBVIEW_RUN_BASE_MBAM_A: "/runs/mbam_seed_a",
                VITE_WEBVIEW_RUN_BASE_MBAM_B: "/runs/mbam_seed_b",
                VITE_WEBVIEW_RUN_BASE_MBAM_C: "/runs/mbam_seed_c",
            },
            "/demo/kvp_demo_1min"
        );
        expect(bases).toEqual({
            A: "/runs/mbam_seed_a",
            B: "/runs/mbam_seed_b",
            C: "/runs/mbam_seed_c",
        });
    });

    it("treats blank per-seed env values as fallback", () => {
        const bases = resolveMbamSeedRunBases(
            {
                VITE_WEBVIEW_RUN_BASE_MBAM_A: "   ",
            },
            "/demo/kvp_demo_1min"
        );
        expect(bases.A).toBe("/demo/kvp_demo_1min");
        expect(bases.B).toBe("/demo/kvp_demo_1min");
        expect(bases.C).toBe("/demo/kvp_demo_1min");
    });
});
