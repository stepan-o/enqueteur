// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, within } from "@testing-library/react";
import DayDetailPanel from "./DayDetailPanel";
import { buildEpisodeView } from "../vm/episodeVm";
import type { StageEpisode } from "../types/stage";

function makeEpisode(overrides?: Partial<StageEpisode>): StageEpisode {
  const base: StageEpisode = {
    episode_id: "ep-x",
    run_id: "run-x",
    episode_index: 0,
    stage_version: 1,
    tension_trend: [0.1, 0.2],
    days: [
      {
        day_index: 0,
        perception_mode: "normal",
        tension_score: 0.42,
        total_incidents: 2,
        supervisor_activity: 0.16,
        narrative: [
          {
            block_id: "b1",
            kind: "beat",
            text: "Something happens",
            day_index: 0,
            agent_name: null,
            tags: [],
          },
          {
            block_id: "b2",
            kind: "aside",
            text: "A quiet moment",
            day_index: 0,
            agent_name: null,
            tags: [],
          },
        ],
        agents: {
          Ava: {
            name: "Ava",
            role: "ops",
            avg_stress: 0.33,
            guardrail_count: 1,
            context_count: 2,
            emotional_read: { mood: "calm" },
            attribution_cause: "system",
            narrative: [],
          },
          Bob: {
            name: "Bob",
            role: "tech",
            avg_stress: 0.21,
            guardrail_count: 0,
            context_count: 1,
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
  return { ...base, ...overrides };
}

describe("DayDetailPanel", () => {
  it("renders day 0 detail from a VM", () => {
    const raw = makeEpisode();
    const vm = buildEpisodeView(raw);

    const { getByText, container } = render(
      <DayDetailPanel episode={vm} dayIndex={0} />
    );

    // Header includes Day 0 and perception mode
    expect(getByText(/Day 0 — perception: normal/)).toBeTruthy();

    // Meta numbers
    expect(getByText(/Tension: 0.42/)).toBeTruthy();
    expect(getByText(/Incidents: 2/)).toBeTruthy();
    expect(getByText(/Supervisor: 0.16/)).toBeTruthy();

    // Narrative
    expect(within(container).getByText(/Something happens/)).toBeTruthy();

    // Agents
    expect(getByText(/Ava/)).toBeTruthy();
    expect(getByText(/Bob/)).toBeTruthy();
  });

  it("shows no data message for a missing day", () => {
    const raw = makeEpisode();
    const vm = buildEpisodeView(raw);
    const { getByText } = render(
      <DayDetailPanel episode={vm} dayIndex={99} />
    );
    expect(getByText(/No data for day 99/)).toBeTruthy();
  });

  it("handles no narrative and no agents gracefully", () => {
    const raw = makeEpisode({
      days: [
        {
          day_index: 0,
          perception_mode: "alert",
          tension_score: 0.1,
          total_incidents: 0,
          supervisor_activity: 0,
          narrative: [],
          agents: {},
        },
      ],
    });
    const vm = buildEpisodeView(raw);

    const { getByText } = render(<DayDetailPanel episode={vm} dayIndex={0} />);

    // Should render empty narrative notice and empty agents notice
    expect(getByText(/No narrative for this day/)).toBeTruthy();
    expect(getByText(/No agent activity recorded for this day/)).toBeTruthy();
  });
});
