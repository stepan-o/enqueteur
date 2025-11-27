// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import * as api from "../api/episodes";

// Let LatestEpisodeView receive an already-shaped EpisodeViewModel from API
vi.mock("../vm/episodeVm", () => ({
  buildEpisodeView: (x: any) => x,
}));

import LatestEpisodeView from "./LatestEpisodeView";

function makeVm() {
  return {
    id: "ep-storyboard",
    runId: "run-storyboard",
    index: 0,
    stageVersion: 1,
    days: [
      { index: 0, tensionScore: 0.1, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
      { index: 1, tensionScore: 0.2, totalIncidents: 1, perceptionMode: "n", supervisorActivity: 0.2 },
    ],
    tensionTrend: [0.1, 0.2],
    agents: [],
    story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
    _raw: {
      episode_id: "ep-storyboard",
      run_id: "run-storyboard",
      episode_index: 0,
      stage_version: 1,
      tension_trend: [0.1, 0.2],
      days: [
        {
          day_index: 0,
          perception_mode: "n",
          tension_score: 0.1,
          total_incidents: 0,
          supervisor_activity: 0,
          agents: {},
          narrative: [
            { block_id: "n0", kind: "beat", text: "Day0 text", day_index: 0, agent_name: null, tags: [] },
          ],
        },
        {
          day_index: 1,
          perception_mode: "n",
          tension_score: 0.2,
          total_incidents: 1,
          supervisor_activity: 0.2,
          agents: {},
          narrative: [
            { block_id: "n1", kind: "beat", text: "Unique Day1 narrative line", day_index: 1, agent_name: null, tags: [] },
          ],
        },
      ],
      agents: {},
      story_arc: null,
      narrative: [],
      long_memory: null,
      character_defs: null,
    },
  } as any;
}

describe("LatestEpisodeView — DayStoryboard integration", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("shows storyboard and syncs selection with DayDetail", async () => {
    const vm = makeVm();
    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);

    render(<LatestEpisodeView />);

    // Storyboard renders two strips
    const strip0 = await screen.findByTestId("day-storyboard-strip-0");
    const strip1 = await screen.findByTestId("day-storyboard-strip-1");
    expect(strip0).toBeTruthy();
    expect(strip1).toBeTruthy();

    // Initially Day 0 is selected in storyboard and DayDetail
    expect(strip0.getAttribute("data-selected")).toBe("true");
    expect(strip1.getAttribute("data-selected")).toBe("false");
    // Day detail header references Day 0
    const dayDetailHeader0 = await screen.findByText(/Day 0 — perception/i);
    expect(dayDetailHeader0).toBeTruthy();

    // Click Day 1 strip
    fireEvent.click(strip1);

    // Selection updates
    expect((await screen.findByTestId("day-storyboard-strip-1")).getAttribute("data-selected")).toBe("true");

    // DayDetail updates to Day 1; unique narrative appears
    const dayDetailHeader1 = await screen.findByText(/Day 1 — perception/i);
    expect(dayDetailHeader1).toBeTruthy();
    const uniques = await screen.findAllByText(/Unique Day1 narrative line/);
    expect(uniques.length).toBeGreaterThan(0);
  });
});
