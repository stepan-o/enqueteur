// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import type { EpisodeViewModel } from "./episodeVm";
import { buildDayStoryboardItems } from "./dayStoryboardVm";

function makeEpisodeVM(opts?: {
  narrativeForDay0?: string | null;
  narrativeForDay1?: string | null;
}): EpisodeViewModel {
  const narrative0 = opts?.narrativeForDay0;
  const narrative1 = opts?.narrativeForDay1;
  return {
    id: "ep",
    runId: "run",
    index: 0,
    stageVersion: 1,
    days: [
      { index: 0, tensionScore: 0.1, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
      { index: 1, tensionScore: 0.2, totalIncidents: 2, perceptionMode: "n", supervisorActivity: 0.5 },
    ],
    agents: [],
    tensionTrend: [0.1, 0.2],
    story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
    _raw: {
      episode_id: "ep",
      run_id: "run",
      episode_index: 0,
      stage_version: 1,
      tension_trend: [0.1, 0.2],
      days: [
        {
          day_index: 0,
          perception_mode: "n",
          tension_score: 0.1,
          total_incidents: 0,
          supervisor_activity: 0,
          agents: {},
          narrative: narrative0 == null ? [] : [{ block_id: "b0", kind: "beat", text: narrative0, day_index: 0, agent_name: null, tags: [] }],
        },
        {
          day_index: 1,
          perception_mode: "n",
          tension_score: 0.2,
          total_incidents: 2,
          supervisor_activity: 0.5,
          agents: {},
          narrative: narrative1 == null ? [] : [{ block_id: "b1", kind: "beat", text: narrative1, day_index: 1, agent_name: null, tags: [] }],
        },
      ],
      agents: {},
      story_arc: null,
      narrative: [],
      long_memory: null,
      character_defs: null,
    },
  } as any;
}

describe("DayStoryboard VM", () => {
  it("returns N items for N days in order", () => {
    const vm = makeEpisodeVM({ narrativeForDay0: "Hello", narrativeForDay1: "World" });
    const items = buildDayStoryboardItems(vm);
    expect(items.length).toBe(2);
    expect(items[0].dayIndex).toBe(0);
    expect(items[1].dayIndex).toBe(1);
  });

  it("uses first narrative text as caption when present", () => {
    const vm = makeEpisodeVM({ narrativeForDay0: "A crisis emerged.", narrativeForDay1: null });
    const items = buildDayStoryboardItems(vm);
    expect(items[0].caption).toMatch(/crisis/);
  });

  it("falls back to neutral caption when narrative missing", () => {
    const vm = makeEpisodeVM({ narrativeForDay0: null, narrativeForDay1: null });
    const items = buildDayStoryboardItems(vm);
    expect(items[0].caption).toMatch(/No major events/);
    expect(items[1].caption).toMatch(/No major events/);
  });

  it("is defensive against malformed episode input", () => {
    // @ts-expect-error intentionally bad input
    const items = buildDayStoryboardItems({} as any);
    expect(items).toEqual([]);
  });

  it("includes narrative lane items with correct order and type", () => {
    const vm = makeEpisodeVM({ narrativeForDay0: "Alpha", narrativeForDay1: "Bravo" });
    const items = buildDayStoryboardItems(vm);
    expect(items[0].narrativeLane.length).toBe(1);
    expect(items[0].narrativeLane[0].lane).toBe("narrative");
    expect(items[0].narrativeLane[0].dayIndex).toBe(0);
    expect(items[0].narrativeLane[0].text).toBe("Alpha");
  });

  it("drops malformed narrative blocks", () => {
    const vm = makeEpisodeVM({ narrativeForDay0: "Keep", narrativeForDay1: "Ok" });
    // Corrupt day 0 narrative array by injecting invalid entries
    (vm as any)._raw.days[0].narrative = [
      null,
      42,
      { block_id: "", kind: "beat", text: "bad", day_index: 0, agent_name: null, tags: [] },
      { block_id: "keep0", kind: "beat", text: "Keep", day_index: 0, agent_name: null, tags: ["x", 5, "y"] },
    ];
    const items = buildDayStoryboardItems(vm);
    expect(items[0].narrativeLane.length).toBe(1);
    expect(items[0].narrativeLane[0].blockId).toBe("keep0");
    expect(items[0].narrativeLane[0].tags).toEqual(["x", "y"]);
  });

  it("classifies tension band based on average tensionScore", () => {
    const vm = makeEpisodeVM({ narrativeForDay0: "A", narrativeForDay1: "B" });
    // Override day-level tension to hit thresholds
    vm.days[0].tensionScore = 0.1; // Low
    vm.days[1].tensionScore = 0.6; // High
    const items = buildDayStoryboardItems(vm);
    expect(items[0].tensionBandClass).toBe("tensionLow");
    expect(items[1].tensionBandClass).toBe("tensionHigh");
  });

  it("builds normalized sparklinePoints from prev and current day tensions", () => {
    const vm = makeEpisodeVM({ narrativeForDay0: "A", narrativeForDay1: "B" });
    vm.days[0].tensionScore = 0.2;
    vm.days[1].tensionScore = 0.5;
    const items = buildDayStoryboardItems(vm);
    const spark1 = items[1].sparklinePoints || [];
    expect(spark1.length).toBe(2);
    // Should normalize to [0,1]
    const min = Math.min(...spark1);
    const max = Math.max(...spark1);
    expect(min).toBe(0);
    expect(max).toBe(1);
  });

  it("returns empty sparklinePoints for missing or flat data", () => {
    const vm = makeEpisodeVM({ narrativeForDay0: "A", narrativeForDay1: "B" });
    // Make both equal -> flat
    vm.days[0].tensionScore = 0.3;
    vm.days[1].tensionScore = 0.3;
    let items = buildDayStoryboardItems(vm);
    expect(items[1].sparklinePoints).toEqual([]);

    // Missing previous day (check first day)
    items = buildDayStoryboardItems(vm);
    expect(items[0].sparklinePoints).toEqual([]);
  });
});
