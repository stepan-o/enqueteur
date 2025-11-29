// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, within } from "@testing-library/react";
import DayDetailPanel from "./DayDetailPanel";
import type { EpisodeViewModel } from "../vm/episodeVm";
import type { StageEpisode } from "../types/stage";

function makeVm(): EpisodeViewModel {
  const raw: StageEpisode = {
    episode_id: "ep",
    run_id: "run",
    episode_index: 0,
    stage_version: 1,
    tension_trend: [],
    days: [
      {
        day_index: 0,
        perception_mode: "normal",
        tension_score: 0.3,
        total_incidents: 1,
        supervisor_activity: 0.2,
        narrative: [
          { block_id: "b1", kind: "recap", text: "Recap text", day_index: 0, agent_name: null, tags: ["recap"] },
          { block_id: "b2", kind: "beat", text: "Beat text", day_index: 0, agent_name: null, tags: ["conflict"] },
        ],
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

describe("DayDetailPanel — V2 narrative integration", () => {
  it("renders NarrativeBlockV2 (data-variant=v2) without crashing", () => {
    const vm = makeVm();
    const { container } = render(<DayDetailPanel episode={vm} dayIndex={0} />);
    const blocks = within(container).getAllByTestId("narrative-block");
    expect(blocks.length).toBeGreaterThan(0);
    // ensure V2 variant marker is present
    expect(blocks[0].getAttribute("data-variant")).toBe("v2");
  });
});
