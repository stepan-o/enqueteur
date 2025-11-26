import { describe, it, expect, expectTypeOf } from "vitest";
import { buildAgentViews, buildPanelAgents, type AgentViewModel } from "./agentVm";
import type { StageEpisode } from "../types/stage";
import type { EpisodeViewModel } from "./episodeVm";

describe("buildAgentViews", () => {
  const baseEpisode: StageEpisode = {
    episode_id: "ep-x",
    run_id: "run-x",
    episode_index: 0,
    stage_version: 1,
    tension_trend: [],
    days: [],
    agents: {
      "Zed": {
        name: "Zed",
        role: "analyst",
        guardrail_total: 3,
        context_total: 1,
        stress_start: null,
        stress_end: 0.4,
        trait_snapshot: null,
        visual: "zed",
        vibe: "calm",
        tagline: "Zed tagline",
      },
      "Ava": {
        name: "Ava",
        role: "operator",
        guardrail_total: 2,
        context_total: 5,
        stress_start: 0.2,
        stress_end: null,
        trait_snapshot: null,
        visual: "ava",
        vibe: "focused",
        tagline: "Ava tagline",
      },
    },
    story_arc: null,
    narrative: [],
    long_memory: null,
    character_defs: null,
  };

  it("normalizes nulls to 0, computes delta, and sorts by name", () => {
    const agents = buildAgentViews(baseEpisode);

    // Type check
    expectTypeOf<AgentViewModel[]>().toMatchTypeOf(agents);

    // Sorted alphabetically: Ava first, then Zed
    expect(agents.map(a => a.name)).toEqual(["Ava", "Zed"]);

    const ava = agents[0];
    const zed = agents[1];

    // Ava: end null -> 0, delta = 0 - 0.2 = -0.2
    expect(ava.stressStart).toBeCloseTo(0.2, 5);
    expect(ava.stressEnd).toBeCloseTo(0, 5);
    expect(ava.stressDelta).toBeCloseTo(-0.2, 5);
    expect(ava.guardrailTotal).toBe(2);
    expect(ava.contextTotal).toBe(5);

    // Zed: start null -> 0, delta = 0.4 - 0 = 0.4
    expect(zed.stressStart).toBeCloseTo(0, 5);
    expect(zed.stressEnd).toBeCloseTo(0.4, 5);
    expect(zed.stressDelta).toBeCloseTo(0.4, 5);
    expect(zed.guardrailTotal).toBe(3);
    expect(zed.contextTotal).toBe(1);
  });

  it("maps roles to vibeColorKey and computes stressTier and tagline fallback", () => {
    const ep: StageEpisode = {
      ...baseEpisode,
      agents: {
        A: { name: "A", role: "supervisor", guardrail_total: 0, context_total: 0, stress_start: 0.1, stress_end: 0.12, trait_snapshot: null, visual: "a", vibe: "", tagline: "" },
        B: { name: "B", role: "operator", guardrail_total: 0, context_total: 0, stress_start: 0.0, stress_end: 0.8, trait_snapshot: null, visual: "b", vibe: "", tagline: "" },
        C: { name: "C", role: "observer", guardrail_total: 0, context_total: 0, stress_start: 0.5, stress_end: 0.45, trait_snapshot: null, visual: "c", vibe: "", tagline: "" },
        D: { name: "D", role: "support", guardrail_total: 0, context_total: 0, stress_start: 0.1, stress_end: 0.2, trait_snapshot: null, visual: "d", vibe: "", tagline: "" },
        E: { name: "E", role: "mystery", guardrail_total: 0, context_total: 0, stress_start: 0.1, stress_end: 0.1, trait_snapshot: null, visual: "e", vibe: "", tagline: "" },
      }
    };
    const list = buildAgentViews(ep);
    const byName: Record<string, any> = Object.fromEntries(list.map(a => [a.name, a]));

    expect(byName["A"].vibeColorKey).toBe("amber");
    expect(byName["B"].vibeColorKey).toBe("teal");
    expect(byName["C"].vibeColorKey).toBe("indigo");
    expect(byName["D"].vibeColorKey).toBe("green");
    expect(byName["E"].vibeColorKey).toBe("neutral");

    // Stress tiers
    expect(byName["B"].stressTier).toBe("high"); // end 0.8
    expect(byName["D"].stressTier === "medium" || byName["D"].stressTier === "none").toBeTruthy(); // safe bound
    expect(byName["C"].stressTier).toBe("cooldown"); // delta negative beyond threshold

    // Tagline fallbacks
    expect(byName["A"].displayTagline).toMatch(/supervisor/i);
    expect(byName["B"].displayTagline).toMatch(/operator/i);
    expect(byName["C"].displayTagline).toMatch(/observer/i);
    expect(byName["D"].displayTagline).toMatch(/support|coordinator/i);
    expect(byName["E"].displayTagline).toMatch(/System agent/i);
  });

  it("buildPanelAgents enriches AgentViewModels with avgStress, latestAttributionCause, and sparkPoints", () => {
    const raw: StageEpisode = {
      episode_id: "ep-p",
      run_id: "run-p",
      episode_index: 0,
      stage_version: 1,
      tension_trend: [],
      days: [
        {
          day_index: 0,
          perception_mode: "normal",
          tension_score: 0,
          total_incidents: 0,
          supervisor_activity: 0,
          narrative: [],
          agents: {
            Ava: { name: "Ava", role: "ops", avg_stress: 0.2, guardrail_count: 1, context_count: 2, emotional_read: null, attribution_cause: "system", narrative: [] },
            Bob: { name: "Bob", role: "tech", avg_stress: 0.4, guardrail_count: 0, context_count: 1, emotional_read: null, attribution_cause: null, narrative: [] },
          },
        },
        {
          day_index: 1,
          perception_mode: "normal",
          tension_score: 0,
          total_incidents: 0,
          supervisor_activity: 0,
          narrative: [],
          agents: {
            Ava: { name: "Ava", role: "ops", avg_stress: 0.3, guardrail_count: 0, context_count: 0, emotional_read: null, attribution_cause: null, narrative: [] },
            Bob: { name: "Bob", role: "tech", avg_stress: 0.5, guardrail_count: 0, context_count: 0, emotional_read: null, attribution_cause: "network", narrative: [] },
          },
        },
      ],
      agents: {
        Ava: { name: "Ava", role: "ops", guardrail_total: 1, context_total: 2, stress_start: 0.1, stress_end: 0.3, trait_snapshot: null, visual: "ava", vibe: "focused", tagline: "" },
        Bob: { name: "Bob", role: "tech", guardrail_total: 0, context_total: 1, stress_start: 0.2, stress_end: 0.5, trait_snapshot: null, visual: "bob", vibe: "chill", tagline: "" },
      },
      story_arc: null,
      narrative: [],
      long_memory: null,
      character_defs: null,
    };

    const vm: EpisodeViewModel = {
      id: raw.episode_id,
      runId: raw.run_id,
      index: raw.episode_index,
      stageVersion: raw.stage_version,
      days: [],
      agents: [],
      tensionTrend: raw.tension_trend,
      story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
      _raw: raw,
    } as unknown as EpisodeViewModel;

    const list = buildPanelAgents(vm);
    expect(list.map(a => a.name)).toEqual(["Ava", "Bob"]);
    const ava = list[0];
    const bob = list[1];

    // avgStress: Ava (0.2 + 0.3)/2 = 0.25
    expect(ava.avgStress).toBeCloseTo(0.25, 5);
    // latest attribution uses last non-null seen over days: Ava -> "system", Bob -> "network"
    expect(ava.latestAttributionCause).toBe("system");
    expect(bob.latestAttributionCause).toBe("network");
    // sparkPoints should be a non-empty string with commas for at least two points
    expect(typeof ava.sparkPoints).toBe("string");
    expect((ava.sparkPoints || "").length).toBeGreaterThan(0);
    expect(ava.sparkPoints).toMatch(/,/);
  });
});
