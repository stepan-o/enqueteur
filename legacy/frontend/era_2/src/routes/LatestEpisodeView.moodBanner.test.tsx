// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import * as episodesApi from "../api/episodes";

// Keep passthrough Episode VM so the API result is used as-is.
vi.mock("../vm/episodeVm", () => ({
    buildEpisodeView: (x: any) => x,
}));

import LatestEpisodeView from "./LatestEpisodeView";

describe("LatestEpisodeView — EpisodeMoodBannerV1", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("renders the mood banner above the episode header when mood is computable", async () => {
        const vm = {
            id: "ep-mood",
            runId: "run-mood",
            index: 0,
            stageVersion: 1,
            days: [
                {
                    index: 0,
                    tensionScore: 0.1,
                    totalIncidents: 0,
                    perceptionMode: "n",
                    supervisorActivity: 0,
                },
                {
                    index: 1,
                    tensionScore: 0.5,
                    totalIncidents: 0,
                    perceptionMode: "n",
                    supervisorActivity: 0,
                },
            ],
            tensionTrend: [0.1, 0.5],
            agents: [],
            story: {
                storyArc: null,
                longMemory: null,
                topLevelNarrative: [
                    {
                        block_id: "b1",
                        kind: "narrative",
                        text: "Alpha attempts a risky calibration.",
                        day_index: 0,
                        agent_name: "Alpha",
                        tags: [],
                    },
                ],
            },
            daySummaries: [
                {
                    dayIndex: 0,
                    tensionDirection: "unknown",
                    tensionChange: null,
                    primaryAgentName: null,
                    primaryAgentStress: null,
                    notableText: "",
                },
                {
                    dayIndex: 1,
                    tensionDirection: "up",
                    tensionChange: 0.4,
                    primaryAgentName: "Alpha",
                    primaryAgentStress: 0.8,
                    notableText: "",
                },
            ],
            _raw: {
                episode_id: "ep-mood",
                run_id: "run-mood",
                episode_index: 0,
                stage_version: 1,
                tension_trend: [0.1, 0.5],
                days: [],
                agents: {},
                story_arc: null,
                narrative: [],
                long_memory: null,
                character_defs: null,
            },
        } as any;

        vi.spyOn(episodesApi, "getLatestEpisode").mockResolvedValue(vm);

        render(<LatestEpisodeView />);

        // Ensure the main view has mounted (Timeline heading shows up)
        await screen.findByText(/Timeline/i);

        // The mood banner should be present
        const banner = await screen.findByTestId("episode-mood-banner");
        expect(banner).to.exist;

        const text = banner.textContent || "";

        // Should include the narrative summary line
        expect(text).to.contain("Alpha attempts a risky calibration.");

        // Sanity check: banner isn't empty
        expect(text.trim().length).to.be.greaterThan(0);
    });
});
