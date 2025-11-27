// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, within } from "@testing-library/react";
import DayDetailPanel from "./DayDetailPanel";
import type { EpisodeViewModel } from "../vm/episodeVm";
import type { StageEpisode } from "../types/stage";
import { stressColor } from "../utils/stressColor";

function makeVm(): EpisodeViewModel {
  const raw: StageEpisode = {
    episode_id: "ep-day",
    run_id: "run-day",
    episode_index: 0,
    stage_version: 1,
    tension_trend: [],
    days: [
      {
        day_index: 0,
        perception_mode: "normal",
        tension_score: 0.25,
        total_incidents: 1,
        supervisor_activity: 0.1,
        narrative: [],
        agents: {
          Ava: {
            name: "Ava",
            role: "ops",
            avg_stress: 0.28,
            guardrail_count: 2,
            context_count: 1,
            emotional_read: null,
            attribution_cause: "system",
            narrative: [],
          },
          Bob: {
            name: "Bob",
            role: "tech",
            avg_stress: 0.52,
            guardrail_count: 0,
            context_count: 3,
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

describe("DayDetailPanel agents — visual language", () => {
  it("renders AgentAvatar and stress dot color per day agent", () => {
    const vm = makeVm();
    const { container } = render(<DayDetailPanel episode={vm} dayIndex={0} />);

    // AgentAvatar (v2) should be present via shared test id
    const avatarEl = within(container).getAllByTestId("agent-avatar-v1");
    expect(avatarEl.length).toBeGreaterThan(0);

    const avaDot = within(container).getByTestId("day-agent-stress-dot-Ava") as HTMLElement;
    const bobDot = within(container).getByTestId("day-agent-stress-dot-Bob") as HTMLElement;
    expect(avaDot.style.backgroundColor).toBe(cssColor(stressColor(0.28)));
    expect(bobDot.style.backgroundColor).toBe(cssColor(stressColor(0.52)));
  });

  it("shows guardrail/context badges per agent with correct counts", () => {
    const vm = makeVm();
    const { container } = render(<DayDetailPanel episode={vm} dayIndex={0} />);
    const gAva = within(container).getByTestId("day-badge-g-Ava");
    const cAva = within(container).getByTestId("day-badge-c-Ava");
    expect(gAva.textContent).toMatch(/G: 2/);
    expect(cAva.textContent).toMatch(/C: 1/);

    const gBob = within(container).getByTestId("day-badge-g-Bob");
    const cBob = within(container).getByTestId("day-badge-c-Bob");
    expect(gBob.textContent).toMatch(/G: 0/);
    expect(cBob.textContent).toMatch(/C: 3/);
  });
});
