// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { buildEpisodeView } from "./episodeVm";
import { buildDaySummary } from "./daySummaryVm";
import type { StageEpisode } from "../types/stage";

function makeEp(trend: number[], agentStresses: number[], dayIndex = 1): StageEpisode {
  // Build two days to allow delta calculation for dayIndex
  const agentsForDay = agentStresses.reduce<Record<string, any>>((acc, s, i) => {
    const name = ["Ava", "Bob", "Cora", "Delta"][i] || `Agent${i}`;
    acc[name] = {
      name,
      role: "ops",
      avg_stress: s,
      guardrail_count: 0,
      context_count: 0,
      emotional_read: null,
      attribution_cause: null,
      narrative: [],
    };
    return acc;
  }, {});

  return {
    episode_id: "ep-1",
    run_id: "run-1",
    episode_index: 0,
    stage_version: 1,
    tension_trend: trend,
    days: [
      {
        day_index: dayIndex - 1,
        perception_mode: "normal",
        tension_score: trend[dayIndex - 1] ?? 0,
        total_incidents: 0,
        supervisor_activity: 0,
        narrative: [],
        agents: {},
      },
      {
        day_index: dayIndex,
        perception_mode: "alert",
        tension_score: trend[dayIndex] ?? 0,
        total_incidents: 0,
        supervisor_activity: 0,
        narrative: [],
        agents: agentsForDay,
      },
    ],
    agents: {},
    story_arc: null,
    narrative: [],
    long_memory: null,
    character_defs: null,
  };
}

describe("buildDaySummary", () => {
  it("direction up with positive delta", () => {
    const raw = makeEp([0.2, 0.4], [0.63]);
    const vm = buildEpisodeView(raw);
    const summary = buildDaySummary(vm, 1);
    expect(summary.tensionDirection).toBe("up");
    expect(summary.tensionChange).toBeCloseTo(0.2, 5);
    expect(summary.primaryAgentName).toBe("Ava");
    expect(summary.primaryAgentStress).toBeCloseTo(0.63, 5);
    expect(summary.notableText).toMatch(/rose/i);
    expect(summary.notableText).toMatch(/Ava/);
  });

  it("direction down with negative delta", () => {
    const raw = makeEp([0.7, 0.6], [0.41]);
    const vm = buildEpisodeView(raw);
    const summary = buildDaySummary(vm, 1);
    expect(summary.tensionDirection).toBe("down");
    expect(summary.notableText).toMatch(/fell/i);
  });

  it("direction flat within ±0.05", () => {
    const raw = makeEp([0.50, 0.53], [0.2]); // delta 0.03 ⇒ flat
    const vm = buildEpisodeView(raw);
    const summary = buildDaySummary(vm, 1);
    expect(summary.tensionDirection).toBe("flat");
    expect(summary.notableText).toMatch(/steady/i);
  });

  it("direction unknown when no previous day", () => {
    // Trend exists but asking for first day (index 0) ⇒ no previous
    const raw: StageEpisode = {
      episode_id: "ep-1",
      run_id: "run-1",
      episode_index: 0,
      stage_version: 1,
      tension_trend: [0.3],
      days: [
        {
          day_index: 0,
          perception_mode: "normal",
          tension_score: 0.3,
          total_incidents: 0,
          supervisor_activity: 0,
          narrative: [],
          agents: {
            Nova: {
              name: "Nova",
              role: "ops",
              avg_stress: 0.41,
              guardrail_count: 0,
              context_count: 0,
              emotional_read: null,
              attribution_cause: null,
              narrative: [],
            },
          },
        },
      ],
      agents: {},
      story_arc: null,
      narrative: [],
      long_memory: null,
      character_defs: null,
    };
    const vm = buildEpisodeView(raw);
    const summary = buildDaySummary(vm, 0);
    expect(summary.tensionDirection).toBe("unknown");
    expect(summary.tensionChange).toBeNull();
    expect(summary.notableText).toMatch(/moderate/i);
    expect(summary.notableText).toMatch(/Nova/);
  });

  it("unknown when trend array missing", () => {
    const raw = makeEp([], [0.5]);
    // Remove trend entirely
    (raw as any).tension_trend = undefined;
    const vm = buildEpisodeView(raw);
    const summary = buildDaySummary(vm, 1);
    expect(summary.tensionDirection).toBe("unknown");
    expect(summary.tensionChange).toBeNull();
  });
});
