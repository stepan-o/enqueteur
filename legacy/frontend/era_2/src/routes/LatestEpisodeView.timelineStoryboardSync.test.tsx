// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import * as api from "../api/episodes";

// Provide VM directly from API layer for route tests
vi.mock("../vm/episodeVm", () => ({
  buildEpisodeView: (x: any) => x,
}));

import LatestEpisodeView from "./LatestEpisodeView";

function makeVm3Days() {
  return {
    id: "ep-sync",
    runId: "run-sync",
    index: 0,
    stageVersion: 1,
    days: [
      { index: 0, tensionScore: 0.1, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
      { index: 1, tensionScore: 0.4, totalIncidents: 1, perceptionMode: "n", supervisorActivity: 0.2 },
      { index: 2, tensionScore: 0.7, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0.3 },
    ],
    tensionTrend: [0.1, 0.4, 0.7],
    agents: [],
    story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
    _raw: {
      episode_id: "ep-sync",
      run_id: "run-sync",
      episode_index: 0,
      stage_version: 1,
      tension_trend: [0.1, 0.4, 0.7],
      days: [
        {
          day_index: 0,
          perception_mode: "n",
          tension_score: 0.1,
          total_incidents: 0,
          supervisor_activity: 0,
          agents: {},
          narrative: [
            { block_id: "n0", kind: "beat", text: "D0", day_index: 0, agent_name: null, tags: [] },
          ],
        },
        {
          day_index: 1,
          perception_mode: "n",
          tension_score: 0.4,
          total_incidents: 1,
          supervisor_activity: 0.2,
          agents: {},
          narrative: [
            { block_id: "n1", kind: "beat", text: "D1", day_index: 1, agent_name: null, tags: [] },
          ],
        },
        {
          day_index: 2,
          perception_mode: "n",
          tension_score: 0.7,
          total_incidents: 0,
          supervisor_activity: 0.3,
          agents: {},
          narrative: [
            { block_id: "n2", kind: "beat", text: "D2", day_index: 2, agent_name: null, tags: [] },
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

describe("LatestEpisodeView — Timeline ↔ Storyboard scroll/selection sync", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("Scenario A: clicking storyboard Day 2 updates timeline and DayDetail", async () => {
    const vm = makeVm3Days();
    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);
    render(<LatestEpisodeView />);

    // wait for storyboard strips
    const s0 = await screen.findByTestId("day-storyboard-strip-0");
    const s2 = await screen.findByTestId("day-storyboard-strip-2");
    expect(s0.getAttribute("data-selected")).toBe("true");
    fireEvent.click(s2);

    // storyboard updated
    expect((await screen.findByTestId("day-storyboard-strip-2")).getAttribute("data-selected")).toBe("true");
    // timeline pill for day 2 should be aria-selected
    const t2 = await screen.findByTestId("timeline-day-2");
    expect(t2.getAttribute("aria-selected")).toBe("true");
    // DayDetail header shows Day 2
    const detailHeader = await screen.findByText(/Day 2 — perception/i);
    expect(detailHeader).toBeTruthy();
  });

  it("Scenario B: clicking a timeline day scrolls storyboard strip into view and selects it", async () => {
    const vm = makeVm3Days();
    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);
    render(<LatestEpisodeView />);

    // mock scrollIntoView on storyboard strip element for day 0
    const container = await screen.findByTestId("day-storyboard-container");
    const day0 = container.querySelector('[data-day-index="0"]') as any;
    day0.scrollIntoView = vi.fn();

    const timelineBtn0 = await screen.findByTestId("timeline-day-0");
    fireEvent.click(timelineBtn0);

    // Storyboard selection applied and scrolled
    expect((await screen.findByTestId("day-storyboard-strip-0")).getAttribute("data-selected")).toBe("true");
    expect(day0.scrollIntoView).toHaveBeenCalled();

    // DayDetail shows Day 0
    const header0 = await screen.findByText(/Day 0 — perception/i);
    expect(header0).toBeTruthy();
  });
});
