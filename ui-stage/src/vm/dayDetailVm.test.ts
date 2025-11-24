// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { buildEpisodeView } from "./episodeVm";
import { buildDayDetail, type DayDetailViewModel } from "./dayDetailVm";
import type { StageEpisode } from "../types/stage";

function makeEp(): StageEpisode {
  return {
    episode_id: "ep-1",
    run_id: "run-1",
    episode_index: 0,
    stage_version: 1,
    tension_trend: [0.2, 0.8],
    days: [
      {
        day_index: 0,
        perception_mode: "normal",
        tension_score: 0.25,
        total_incidents: 1,
        supervisor_activity: 0,
        narrative: [
          {
            block_id: "n1",
            kind: "beat",
            text: "A calm beginning",
            day_index: 0,
            agent_name: null,
            tags: ["intro"],
          },
        ],
        agents: {
          Bob: {
            name: "Bob",
            role: "tech",
            avg_stress: 0.4,
            guardrail_count: 1,
            context_count: 2,
            emotional_read: { mood: "ok" },
            attribution_cause: "system",
            narrative: [],
          },
          Ava: {
            name: "Ava",
            role: "ops",
            avg_stress: null as unknown as number, // ensure null→0 normalization via casting
            guardrail_count: 0,
            context_count: null as unknown as number,
            emotional_read: null,
            attribution_cause: null,
            narrative: [],
          },
        },
      },
      {
        day_index: 1,
        perception_mode: "alert",
        tension_score: 0.7,
        total_incidents: 3,
        supervisor_activity: 0.2,
        narrative: [],
        agents: {},
      },
    ],
    agents: {
      Bob: {
        name: "Bob",
        role: "tech",
        guardrail_total: 2,
        context_total: 4,
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
        stress_start: 0.1,
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
}

describe("buildDayDetail", () => {
  it("builds full model for day 0", () => {
    const raw = makeEp();
    const vm = buildEpisodeView(raw);

    const detail = buildDayDetail(vm, 0);
    expect(detail.index).toBe(0);
    expect(detail.perceptionMode).toBe("normal");
    expect(detail.tensionScore).toBeCloseTo(0.25, 5);
    expect(detail.totalIncidents).toBe(1);
    expect(detail.supervisorActivity).toBe(0);
    expect(detail.narrative.length).toBe(1);
    expect(detail.agents.length).toBe(2);
  });

  it("returns empty VM when no such day", () => {
    const raw = makeEp();
    const vm = buildEpisodeView(raw);
    const detail = buildDayDetail(vm, 99);
    const empty: DayDetailViewModel = {
      index: 99,
      perceptionMode: "unknown",
      tensionScore: 0,
      totalIncidents: 0,
      supervisorActivity: 0,
      narrative: [],
      agents: [],
    };
    expect(detail).toEqual(empty);
  });

  it("agent sorting (alphabetical by name)", () => {
    const vm = buildEpisodeView(makeEp());
    const detail = buildDayDetail(vm, 0);
    expect(detail.agents.map((a) => a.name)).toEqual(["Ava", "Bob"]);
  });

  it("normalizes null numeric fields to 0", () => {
    const vm = buildEpisodeView(makeEp());
    const detail = buildDayDetail(vm, 0);
    const ava = detail.agents.find((a) => a.name === "Ava")!;
    expect(ava.avgStress).toBe(0);
    expect(ava.contextCount).toBe(0);
  });

  it("narrative passthrough", () => {
    const vm = buildEpisodeView(makeEp());
    const detail = buildDayDetail(vm, 0);
    expect(detail.narrative[0].text).toMatch(/calm beginning/);
  });

  it("emotional_read + attribution passthrough", () => {
    const vm = buildEpisodeView(makeEp());
    const detail = buildDayDetail(vm, 0);
    const bob = detail.agents.find((a) => a.name === "Bob")!;
    expect(bob.emotionalRead).toEqual({ mood: "ok" });
    expect(bob.attributionCause).toBe("system");
  });

  it("handles missing _raw safely (does not throw)", () => {
    // Craft a minimal EpisodeViewModel-like object without _raw
    const fake: any = {
      id: null,
      runId: null,
      index: 0,
      stageVersion: 1,
      days: [],
      agents: [],
      tensionTrend: [],
    };
    const detail = buildDayDetail(fake, 0);
    expect(detail.index).toBe(0);
    expect(detail.agents.length).toBe(0);
  });
});
