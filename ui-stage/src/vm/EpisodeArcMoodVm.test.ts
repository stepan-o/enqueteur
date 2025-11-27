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

  it("maps class to icon and new direction-aware labels", () => {
    const calm = buildEpisodeArcMood(makeEpisode([0.1, 0.11, 0.1]));
    expect(calm.label).toMatch(/Steady State/i);
    expect(calm.icon).toBe("🌿");

    const spikeUp = buildEpisodeArcMood(makeEpisode([0.0, 0.6]));
    expect(spikeUp.label).toMatch(/Spike|Critical/i);
    expect(spikeUp.icon).toBe("⚡");
  });

  it("uses top-level narrative first block text for summary when available", () => {
    const ep = makeEpisode([0.1, 0.2], "Hello world summary");
    const mood = buildEpisodeArcMood(ep);
    expect(mood.summaryLine).toBe("Hello world summary");
  });

  it("falls back to direction-aligned default summary when narrative missing", () => {
    const epFlat = makeEpisode([0.12, 0.13, 0.11]);
    const moodFlat = buildEpisodeArcMood(epFlat);
    expect(moodFlat.summaryLine).toMatch(/relatively steady/i);

    const epUp = makeEpisode([0.1, 0.2, 0.4]);
    const moodUp = buildEpisodeArcMood(epUp);
    expect(moodUp.summaryLine).toMatch(/builds across/i);

    const epDown = makeEpisode([0.5, 0.4, 0.3]);
    const moodDown = buildEpisodeArcMood(epDown);
    expect(moodDown.summaryLine).toMatch(/eases off/i);
  });

  it("guards malformed tension_trend gracefully (non-array, NaN)", () => {
    const ep = makeEpisode("not-an-array", "S");
    const mood = buildEpisodeArcMood(ep);
    expect(["calm", "minor", "medium", "spike"]).toContain(mood.tensionClass);
  });

  it("keeps tension class based on global delta regardless of path (back-compat)", () => {
    // Both trends have the same min=0.1 and max=0.5, but different daily paths.
    const increasing = buildEpisodeArcMood(makeEpisode([0.1, 0.3, 0.5])).tensionClass;
    const spikeThenEase = buildEpisodeArcMood(makeEpisode([0.1, 0.5, 0.2])).tensionClass;
    expect(increasing).toBe(spikeThenEase); // same global delta → same class
  });

  it("direction-aware: upward medium arc → Building Pressure", () => {
    const mood = buildEpisodeArcMood(makeEpisode([0.1, 0.25, 0.5])); // delta 0.4 → medium, slope up
    expect(mood.tensionClass).toBe("medium");
    expect(mood.label).toMatch(/Building Pressure/i);
    expect(mood.icon).toBe("📈");
  });

  it("direction-aware: downward easing arc never says Building Pressure", () => {
    const mood = buildEpisodeArcMood(makeEpisode([0.6, 0.5, 0.35])); // delta 0.25 → medium, slope down
    expect(mood.tensionClass).toBe("medium");
    expect(mood.label).toMatch(/Softening Arc/i);
    expect(mood.label).not.toMatch(/Building Pressure/i);
    expect(mood.icon).toBe("📉");
  });

  it("flat low-delta → Steady State", () => {
    const mood = buildEpisodeArcMood(makeEpisode([0.4, 0.41, 0.39]));
    expect(mood.tensionClass).toBe("calm");
    expect(mood.label).toMatch(/Steady State/i);
  });

  it("mixed spiky arc → Volatile Arc with wobble icon", () => {
    const mood = buildEpisodeArcMood(makeEpisode([0.2, 0.6, 0.25, 0.7])); // spike + mixed
    expect(mood.tensionClass).toBe("spike");
    expect(mood.label).toMatch(/Volatile Arc/i);
    // v2.1: mixed (any class) uses wobble icon
    expect(mood.icon).toBe("🌀");
  });

  it("mixed medium arc uses wobble icon", () => {
    const mood = buildEpisodeArcMood(makeEpisode([0.2, 0.35, 0.25, 0.5, 0.3])); // medium delta + several sign changes
    expect(mood.tensionClass).toBe("medium");
    // Icon should be wobble for mixed non-spike
    expect(mood.icon).toBe("🌀");
  });
});
