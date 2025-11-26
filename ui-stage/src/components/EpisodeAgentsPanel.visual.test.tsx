// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import EpisodeAgentsPanel from "./EpisodeAgentsPanel";
import type { EpisodeViewModel } from "../vm/episodeVm";
import type { StageEpisode } from "../types/stage";
import { stressColor } from "../utils/stressColor";

function makeVm(): EpisodeViewModel {
  const raw: StageEpisode = {
    episode_id: "ep-agents",
    run_id: "run-x",
    episode_index: 0,
    stage_version: 1,
    tension_trend: [],
    days: [
      {
        day_index: 0,
        perception_mode: "normal",
        tension_score: 0.2,
        total_incidents: 0,
        supervisor_activity: 0,
        narrative: [],
        agents: {
          Ava: {
            name: "Ava",
            role: "ops",
            avg_stress: 0.32,
            guardrail_count: 1,
            context_count: 2,
            emotional_read: null,
            attribution_cause: "system",
            narrative: [],
          },
          Bob: {
            name: "Bob",
            role: "tech",
            avg_stress: 0.12,
            guardrail_count: 0,
            context_count: 0,
            emotional_read: null,
            attribution_cause: null,
            narrative: [],
          },
        },
      },
      {
        day_index: 1,
        perception_mode: "alert",
        tension_score: 0.5,
        total_incidents: 1,
        supervisor_activity: 0.1,
        narrative: [],
        agents: {
          Ava: {
            name: "Ava",
            role: "ops",
            avg_stress: 0.40,
            guardrail_count: 0,
            context_count: 0,
            emotional_read: null,
            attribution_cause: null,
            narrative: [],
          },
        },
      },
    ],
    agents: {
      Ava: {
        name: "Ava",
        role: "ops",
        guardrail_total: 1,
        context_total: 2,
        stress_start: 0.2,
        stress_end: 0.4,
        trait_snapshot: null,
        visual: "ava",
        vibe: "focused",
        tagline: "",
      },
      Bob: {
        name: "Bob",
        role: "tech",
        guardrail_total: 0,
        context_total: 0,
        stress_start: 0.1,
        stress_end: 0.12,
        trait_snapshot: null,
        visual: "",
        vibe: "chill",
        tagline: "",
      },
    },
    story_arc: null,
    narrative: [],
    long_memory: null,
    character_defs: null,
  };

  return {
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
}

function cssColor(val: string): string {
  const el = document.createElement("div");
  el.style.backgroundColor = val;
  return el.style.backgroundColor;
}

describe("EpisodeAgentsPanel — visual language", () => {
  it("renders AgentAvatar and stress dot with correct color", () => {
    const vm = makeVm();
    const { container } = render(<EpisodeAgentsPanel episode={vm} />);

    // Avatar should be rendered via AgentAvatar (v2) with shared data-testid
    const bobRow = within(container).getByText(/Bob/).closest("li") as HTMLElement;
    const avatars = within(bobRow!).getAllByTestId("agent-avatar-v1");
    expect(avatars.length).toBeGreaterThan(0);

    // Stress dot color for Ava based on her avg across days (~0.36 → orange #FF9F1C)
    const avaDot = within(container).getByTestId("agent-stress-dot-Ava") as HTMLElement;
    const expected = cssColor(stressColor(0.36));
    expect(avaDot.style.backgroundColor).toBe(expected);
  });

  it("renders a sparkline SVG per agent", () => {
    const vm = makeVm();
    const { container } = render(<EpisodeAgentsPanel episode={vm} />);
    // Prefer role-based query; fall back to label if role not supported
    const imgs = screen.queryAllByRole("img");
    if (imgs.length >= 2) {
      expect(imgs.length).toBeGreaterThanOrEqual(2);
    } else {
      const byLabel = within(container).queryAllByLabelText(/Stress sparkline for/i);
      expect(byLabel.length).toBeGreaterThanOrEqual(2);
    }
  });

  it("shows guardrail/context badges with numeric values", () => {
    const vm = makeVm();
    const { container } = render(<EpisodeAgentsPanel episode={vm} />);
    const gAva = within(container).getByTestId("badge-g-Ava");
    const cAva = within(container).getByTestId("badge-c-Ava");
    expect(gAva.textContent).toMatch(/G: 1/);
    expect(cAva.textContent).toMatch(/C: 2/);
  });
});
