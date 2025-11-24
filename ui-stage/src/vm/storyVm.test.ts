import { describe, it, expect } from "vitest";
import { buildEpisodeStory, type EpisodeStoryViewModel } from "./storyVm";
import type { StageEpisode, StageNarrativeBlock } from "../types/stage";

describe("buildEpisodeStory", () => {
  it("normalizes null story_arc and long_memory to null and narrative to [] when missing", () => {
    const ep: StageEpisode = {
      episode_id: "e1",
      run_id: null,
      episode_index: 0,
      stage_version: 1,
      tension_trend: [],
      days: [],
      agents: {},
      // story_arc, long_memory, narrative intentionally omitted to simulate missing
      // @ts-expect-error allow omission to test normalization
    } as unknown as StageEpisode;

    const vm: EpisodeStoryViewModel = buildEpisodeStory(ep);
    expect(vm.storyArc).toBeNull();
    expect(vm.longMemory).toBeNull();
    expect(vm.topLevelNarrative).toEqual([]);
  });

  it("passes through narrative blocks when present", () => {
    const blocks: StageNarrativeBlock[] = [
      {
        block_id: "b1",
        kind: "recap",
        text: "Day 0 overview",
        day_index: 0,
        agent_name: null,
        tags: ["recap"],
      },
    ];
    const ep: StageEpisode = {
      episode_id: "e2",
      run_id: "r2",
      episode_index: 1,
      stage_version: 1,
      tension_trend: [0.1],
      days: [],
      agents: {},
      story_arc: null,
      narrative: blocks,
      long_memory: null,
      character_defs: null,
    };

    const vm = buildEpisodeStory(ep);
    expect(vm.topLevelNarrative).toBe(blocks);
    expect(vm.storyArc).toBeNull();
    expect(vm.longMemory).toBeNull();
  });

  it("does not throw when optional fields are absent", () => {
    const ep = {
      episode_id: null,
      run_id: null,
      episode_index: 2,
      stage_version: 1,
      tension_trend: [],
      days: [],
      agents: {},
    } as unknown as StageEpisode;

    expect(() => buildEpisodeStory(ep)).not.toThrow();
  });
});
