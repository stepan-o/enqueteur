// ui-stage/src/vm/episodeVm.snapshot.test.ts
import { describe, it, expect } from "vitest";
import { buildEpisodeView } from "./episodeVm";
import type { StageEpisode } from "../types/stage";

describe("buildEpisodeView snapshot", () => {
    it("produces stable VM shape", () => {
        const ep: StageEpisode = {
            episode_id: "ep-1",
            run_id: "run-1",
            episode_index: 0,
            stage_version: 1,
            tension_trend: [0.1, 0.3],
            days: [],
            agents: {},
            story_arc: null,
            narrative: [],
            long_memory: null,
            character_defs: null,
        };
        const vm = buildEpisodeView(ep);
        expect(vm).toMatchInlineSnapshot();
    });
});
