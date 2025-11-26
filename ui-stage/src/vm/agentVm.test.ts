import { describe, it, expect, expectTypeOf } from "vitest";
import { buildAgentViews, type AgentViewModel } from "./agentVm";
import type { StageEpisode } from "../types/stage";

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
});
