// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { buildEpisodeArcMood } from "./episodeArcMoodVm";

function makeEpisode(tensionTrend: any, firstText?: string) {
  return {
    id: "ep",
    runId: "run",
    index: 0,
    stageVersion: 1,
    days: [],
    agents: [],
    tensionTrend,
    story: {
      storyArc: null,
      longMemory: null,
      topLevelNarrative: firstText != null ? [{ block_id: "b", kind: "recap", text: firstText, day_index: 0, agent_name: null, tags: [] }] : [],
    },
    _raw: {} as any,
  } as any;
}

describe("episodeArcMoodVm", () => {
  it("classifies calm/minor/medium/spike by delta across trend", () => {
    expect(buildEpisodeArcMood(makeEpisode([0.1, 0.15])).tensionClass).toBe("calm");
    expect(buildEpisodeArcMood(makeEpisode([0.1, 0.3])).tensionClass).toBe("minor");
    expect(buildEpisodeArcMood(makeEpisode([0.1, 0.54])).tensionClass).toBe("medium");
    expect(buildEpisodeArcMood(makeEpisode([0.05, 0.6])).tensionClass).toBe("spike");
  });

  it("maps class to human label and icon", () => {
    const calm = buildEpisodeArcMood(makeEpisode([0.1, 0.19]));
    expect(calm.label).toMatch(/Calm/i);
    expect(calm.icon).toBe("🌿");

    const spike = buildEpisodeArcMood(makeEpisode([0.0, 0.6]));
    expect(spike.label).toMatch(/Spike/i);
    expect(spike.icon).toBe("⚡");
  });

  it("uses top-level narrative first block text for summary when available", () => {
    const ep = makeEpisode([0.1, 0.2], "Hello world summary");
    const mood = buildEpisodeArcMood(ep);
    expect(mood.summaryLine).toBe("Hello world summary");
  });

  it("falls back to default summary when narrative missing or malformed", () => {
    const ep = makeEpisode([0.1, 0.2]);
    const mood = buildEpisodeArcMood(ep);
    expect(mood.summaryLine).toMatch(/subtle shifts/i);
  });

  it("guards malformed tension_trend gracefully (non-array, NaN)", () => {
    const ep = makeEpisode("not-an-array", "S");
    const mood = buildEpisodeArcMood(ep);
    expect(["calm", "minor", "medium", "spike"]).toContain(mood.tensionClass);
  });
});
