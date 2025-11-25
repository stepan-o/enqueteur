// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import DayDetailPanel from "./DayDetailPanel";
import type { EpisodeViewModel } from "../vm/episodeVm";
import type { StageEpisode } from "../types/stage";

function makeVm(withMalformed = false): EpisodeViewModel {
  const narrative = withMalformed
    ? [
        // valid block
        {
          block_id: "n1",
          kind: "day_intro",
          text: "The floor is steady with a subtle edge.",
          day_index: 0,
          agent_name: null,
          tags: ["intro"],
        },
        // malformed: missing tags, non-string agent_name
        {
          block_id: "n2",
          kind: "supervisor",
          text: "Supervisor checks in periodically…",
          day_index: 0,
          agent_name: 123 as unknown as string,
          // @ts-expect-error omit tags to test graceful handling
        },
      ]
    : [
        {
          block_id: "n1",
          kind: "day_intro",
          text: "The floor is steady with a subtle edge.",
          day_index: 0,
          agent_name: null,
          tags: ["intro"],
        },
        {
          block_id: "n3",
          kind: "day_outro",
          text: "Shift complete; systems hold.",
          day_index: 0,
          agent_name: null,
          tags: ["outro"],
        },
      ];

  const raw: StageEpisode = {
    episode_id: "ep-narr",
    run_id: "run-narr",
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
        narrative,
        agents: {},
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

describe("DayDetailPanel — narrative formatting", () => {
  it("renders narrative blocks using NarrativeBlock component", () => {
    const vm = makeVm(false);
    const { container } = render(<DayDetailPanel episode={vm} dayIndex={0} />);
    const section = screen.getByLabelText("Day narrative");
    expect(section).toBeTruthy();
    const blocks = within(container).getAllByTestId("narrative-block");
    expect(blocks.length).toBe(2);
  });

  it("narrative count matches input and tags render correctly", () => {
    const vm = makeVm(false);
    const { container } = render(<DayDetailPanel episode={vm} dayIndex={0} />);
    const blocks = within(container).getAllByTestId("narrative-block");
    expect(blocks.length).toBe(2);
    // first block should include tag 'intro'
    expect(blocks[0].textContent || "").toMatch(/intro/);
    // second block should include tag 'outro'
    expect(blocks[1].textContent || "").toMatch(/outro/);
  });

  it("does not crash with malformed or partially missing fields", () => {
    const vm = makeVm(true);
    const { container } = render(<DayDetailPanel episode={vm} dayIndex={0} />);
    const blocks = within(container).getAllByTestId("narrative-block");
    expect(blocks.length).toBe(2);
    // Malformed block omitted tags gracefully (no tags container required)
    // Ensure text content of both blocks is present
    expect(container.textContent || "").toMatch(/Supervisor checks in periodically/);
  });
});
