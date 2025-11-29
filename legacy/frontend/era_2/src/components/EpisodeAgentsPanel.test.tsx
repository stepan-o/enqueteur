// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, within } from "@testing-library/react";
import EpisodeAgentsPanel from "./EpisodeAgentsPanel";
import type { EpisodeViewModel } from "../vm/episodeVm";
import type { StageEpisode } from "../types/stage";

function makeVm(rawOverrides?: Partial<StageEpisode>): EpisodeViewModel {
  const raw: StageEpisode = {
    episode_id: "ep-1",
    run_id: "run-1",
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
          Ava: {
            name: "Ava",
            role: "ops",
            avg_stress: 0.315,
            guardrail_count: 1,
            context_count: 2,
            emotional_read: null,
            attribution_cause: "system",
            narrative: [],
          },
          Bob: {
            name: "Bob",
            role: "tech",
            avg_stress: 0.2,
            guardrail_count: 0,
            context_count: 1,
            emotional_read: null,
            attribution_cause: null,
            narrative: [],
          },
        },
      },
    ],
    agents: {
      Bob: {
        name: "Bob",
        role: "tech",
        guardrail_total: 2,
        context_total: 4,
        stress_start: 0.1,
        stress_end: 0.2,
        trait_snapshot: null,
        visual: "bob",
        vibe: "chill",
        tagline: "",
      },
      Ava: {
        name: "Ava",
        role: "ops",
        guardrail_total: 1,
        context_total: 2,
        stress_start: 0.3,
        stress_end: 0.1,
        trait_snapshot: null,
        visual: "ava",
        vibe: "focused",
        tagline: "",
      },
    },
    story_arc: null,
    narrative: [],
    long_memory: null,
    character_defs: null,
    ...rawOverrides,
  };

  return {
    id: raw.episode_id,
    runId: raw.run_id,
    index: raw.episode_index,
    stageVersion: raw.stage_version,
    days: [],
    agents: [],
    tensionTrend: raw.tension_trend ?? [],
    story: {
      storyArc: null,
      longMemory: null,
      topLevelNarrative: [],
    },
    _raw: raw,
  };
}

describe("EpisodeAgentsPanel", () => {
  it("renders all agents sorted alphabetically", () => {
    const vm = makeVm();
    const { container } = render(<EpisodeAgentsPanel episode={vm} />);
    const items = within(container).getAllByRole("listitem");
    expect(items.length).toBe(2);
    const text0 = items[0].textContent || "";
    const text1 = items[1].textContent || "";
    expect(text0.startsWith("Ava")).toBe(true);
    expect(text1.startsWith("Bob")).toBe(true);
  });

  it("formats average stress to 2 decimals and shows guardrail/context counts", () => {
    const vm = makeVm();
    const { container } = render(<EpisodeAgentsPanel episode={vm} />);
    const text = container.textContent || "";
    expect(text).toMatch(/avg stress 0.32/); // 0.315 → 0.32
    expect(text).toMatch(/guardrails 1/);
    expect(text).toMatch(/context 2/);
  });

  it("handles attribution cause present/absent", () => {
    const vm = makeVm();
    const { container } = render(<EpisodeAgentsPanel episode={vm} />);
    const text = container.textContent || "";
    // Ava has cause system, Bob has none
    expect(text).toMatch(/cause system/);
    // Ensure we don't render 'cause' for Bob specifically by checking only one match
    const matches = text.match(/cause /g) || [];
    expect(matches.length).toBe(1);
  });

  it("renders empty state when no agents", () => {
    const vm = makeVm({ agents: {} });
    const { container, getByText } = render(<EpisodeAgentsPanel episode={vm} />);
    expect(getByText(/No agents recorded for this episode/i)).toBeTruthy();
    expect(within(container).queryAllByRole("listitem").length).toBe(0);
  });
});
