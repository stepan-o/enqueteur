import { describe, it, expect, expectTypeOf } from "vitest";
import { buildEpisodeView, type EpisodeViewModel } from "./episodeVm";
import type { StageEpisode } from "../types/stage";

describe("buildEpisodeView", () => {
  const ep: StageEpisode = {
    episode_id: "ep-42",
    run_id: "run-9",
    episode_index: 3,
    stage_version: 1,
    tension_trend: [0.1, 0.5],
    days: [
      {
        day_index: 0,
        perception_mode: "normal",
        tension_score: 0.1,
        agents: {},
        total_incidents: 0,
        supervisor_activity: 0,
        narrative: [],
      },
      {
        day_index: 1,
        perception_mode: "alert",
        tension_score: 0.5,
        agents: {},
        total_incidents: 2,
        supervisor_activity: 0.2,
        narrative: [],
      },
    ],
    agents: {
      Bob: {
        name: "Bob",
        role: "tech",
        guardrail_total: 1,
        context_total: 2,
        stress_start: 0.3,
        stress_end: 0.6,
        trait_snapshot: null,
        visual: "bob",
        vibe: "chill",
        tagline: "Beep bop.",
      },
      Ava: {
        name: "Ava",
        role: "ops",
        guardrail_total: 0,
        context_total: 1,
        stress_start: null,
        stress_end: 0.2,
        trait_snapshot: null,
        visual: "ava",
        vibe: "focused",
        tagline: "On it.",
      },
    },
    story_arc: null,
    narrative: [],
    long_memory: null,
    character_defs: null,
  };

  it("maps top-level fields and composes sub-VMs", () => {
    const vm = buildEpisodeView(ep);

    // Type check for EpisodeViewModel
    expectTypeOf<EpisodeViewModel>().toMatchTypeOf(vm);

    expect(vm.id).toBe("ep-42");
    expect(vm.runId).toBe("run-9");
    expect(vm.index).toBe(3);
    expect(vm.stageVersion).toBe(1);

    // Days
    expect(vm.days.length).toBe(2);
    expect(vm.days[0].index).toBe(0);
    expect(vm.days[1].tensionScore).toBeCloseTo(0.5, 5);

    // Agents (sorted alphabetically: Ava then Bob)
    expect(vm.agents.length).toBe(2);
    expect(vm.agents[0].name).toBe("Ava");
    expect(vm.agents[1].name).toBe("Bob");

    // Tension trend passthrough
    expect(vm.tensionTrend).toEqual([0.1, 0.5]);
  });

  it("computes optional daySummaries aligned with days and trend direction", () => {
    const ep2: StageEpisode = {
      episode_id: "ep-43",
      run_id: "run-10",
      episode_index: 1,
      stage_version: 1,
      // Trend: 0 → 0.2 (up), 0.2 → 0.2 (flat), 0.2 → 0.1 (down)
      tension_trend: [0.0, 0.2, 0.2, 0.1],
      days: [
        { day_index: 0, perception_mode: "normal", tension_score: 0.0, agents: {}, total_incidents: 0, supervisor_activity: 0, narrative: [] },
        { day_index: 1, perception_mode: "normal", tension_score: 0.2, agents: {}, total_incidents: 0, supervisor_activity: 0, narrative: [] },
        { day_index: 2, perception_mode: "normal", tension_score: 0.2, agents: {}, total_incidents: 0, supervisor_activity: 0, narrative: [] },
        { day_index: 3, perception_mode: "normal", tension_score: 0.1, agents: {}, total_incidents: 0, supervisor_activity: 0, narrative: [] },
      ],
      agents: {},
      story_arc: null,
      narrative: [],
      long_memory: null,
      character_defs: null,
    };

    const vm = buildEpisodeView(ep2);
    expect(Array.isArray(vm.daySummaries)).toBe(true);
    expect(vm.daySummaries!.length).toBe(vm.days.length);
    // Indices should match 0..3
    expect(vm.daySummaries!.map((s) => s.dayIndex)).toEqual([0, 1, 2, 3]);
    // Direction logic vs previous day
    const dirs = vm.daySummaries!.map((s) => s.tensionDirection);
    expect(dirs[0]).toBe("unknown");
    expect(dirs[1]).toBe("up");
    expect(dirs[2]).toBe("flat");
    expect(dirs[3]).toBe("down");
  });
});
