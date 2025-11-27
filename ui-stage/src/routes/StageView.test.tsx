// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, within, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as api from "../api/episodes";

// For route tests we typically have buildEpisodeView passthrough the VM-shaped object
vi.mock("../vm/episodeVm", () => ({
  buildEpisodeView: (x: any) => x,
}));

import StageView from "./StageView";

function makeEpisodeVm() {
  const vm: any = {
    id: "ep-stage",
    runId: "run-stage",
    index: 0,
    stageVersion: 1,
    days: [
      { index: 0, tensionScore: 0.2, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
      { index: 1, tensionScore: 0.7, totalIncidents: 2, perceptionMode: "n", supervisorActivity: 0 },
    ],
    agents: [],
    tensionTrend: [0.2, 0.7],
    story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
    daySummaries: [
      { dayIndex: 0, tensionDirection: "up", tensionChange: 0.2, primaryAgentName: "Ava", primaryAgentStress: 0.3, notableText: "" },
      { dayIndex: 1, tensionDirection: "up", tensionChange: 0.5, primaryAgentName: "Bob", primaryAgentStress: 0.8, notableText: "" },
    ],
    _raw: {
      episode_id: "ep-stage",
      run_id: "run-stage",
      episode_index: 0,
      stage_version: 1,
      tension_trend: [0.2, 0.7],
      days: [
        {
          day_index: 0,
          perception_mode: "n",
          tension_score: 0.2,
          total_incidents: 0,
          supervisor_activity: 0,
          narrative: [],
          agents: {
            Ava: { name: "Ava", role: "ops", avg_stress: 0.3, guardrail_count: 0, context_count: 0, emotional_read: null, attribution_cause: null, narrative: [] },
          },
        },
        {
          day_index: 1,
          perception_mode: "n",
          tension_score: 0.7,
          total_incidents: 2,
          supervisor_activity: 0,
          narrative: [],
          agents: {
            Bob: { name: "Bob", role: "tech", avg_stress: 0.8, guardrail_count: 0, context_count: 0, emotional_read: null, attribution_cause: null, narrative: [] },
          },
        },
      ],
      agents: {
        Ava: { name: "Ava", role: "operator", guardrail_total: 1, context_total: 2, stress_start: 0.1, stress_end: 0.3, trait_snapshot: null, visual: "ava", vibe: "focused", tagline: "" },
        Bob: { name: "Bob", role: "tech", guardrail_total: 0, context_total: 1, stress_start: 0.4, stress_end: 0.8, trait_snapshot: null, visual: "bob", vibe: "chill", tagline: "" },
      },
      story_arc: null,
      narrative: [],
      long_memory: null,
      character_defs: null,
    },
  };
  return vm;
}

describe("StageView route", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders title, day selector, Stage Map, and world summary for Day 0; day change updates map", async () => {
    const vm = makeEpisodeVm();
    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);

    render(
      <MemoryRouter initialEntries={["/episodes/ep-stage/stage"]}>
        <Routes>
          <Route path="/episodes/:id/stage" element={<StageView />} />
        </Routes>
      </MemoryRouter>
    );

    // Stage Map region should be present and show Day 0 initially
    const group = await screen.findByTestId("stage-map-group");
    const tiles = within(group).getAllByRole("img");
    // Should be low tier for Day 0
    tiles.forEach((el) => expect(el.getAttribute("data-tension-tier")).toBe("low"));

    // Click Day 1 on timeline to change selection
    const tlBtn1 = await screen.findByTestId("timeline-day-1");
    fireEvent.click(tlBtn1);

    // Now some tiles should reflect high tier
    const highTiles = Array.from(document.querySelectorAll('[data-tension-tier="high"]'));
    expect(highTiles.length).toBeGreaterThan(0);

    // Detail panel generic summary should mention Day 1 when no agent selected
    const details = await screen.findByLabelText(/Stage details panel/i);
    expect(within(details).getByText(/Day 1/)).toBeTruthy();
  });

  it("clicking agent chip focuses agent in detail panel with aria-label on button", async () => {
    const vm = makeEpisodeVm();
    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);
    render(
      <MemoryRouter initialEntries={["/episodes/ep-stage/stage"]}>
        <Routes>
          <Route path="/episodes/:id/stage" element={<StageView />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for timeline and for Stage Map to reflect Day 0 selection
    await screen.findByTestId("timeline-day-0");
    const region = await screen.findByRole("region", { name: /Stage map for Day 0/i });
    const group = within(region).getByRole("group", { name: /Stage map/i });
    const btn = within(group).getByRole("button", { name: /Focus on agent Ava for Day 0/i });
    fireEvent.click(btn);

    // Detail panel shows agent-focused content (name, role or stat text)
    const focusPanel = await screen.findByTestId("agent-focus-panel");
    expect(within(focusPanel).getByText(/Ava/)).toBeTruthy();
    expect(within(focusPanel).getByText(/avg stress/i)).toBeTruthy();
  });

  it("handles episodes with no days gracefully", async () => {
    const vm = makeEpisodeVm();
    vm.days = [];
    vm._raw.days = [];
    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);
    render(
      <MemoryRouter initialEntries={["/episodes/ep-stage/stage"]}>
        <Routes>
          <Route path="/episodes/:id/stage" element={<StageView />} />
        </Routes>
      </MemoryRouter>
    );
    // Neutral map caption and detail panel empty-state
    const region = await screen.findByRole("region", { name: /Stage map \(no day selected\)/i });
    const mapGroup = within(region).getByRole("group", { name: /Stage map/i });
    expect(within(mapGroup).getByText(/No day selected/i)).toBeTruthy();
    // Empty-state copy should be present
    expect(await screen.findByText(/No days available for this episode/i)).toBeTruthy();
  });
});
