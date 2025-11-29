// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, within } from "@testing-library/react";
import * as api from "../api/episodes";

// Provide VM passthrough so we can inject EpisodeViewModel-like object
vi.mock("../vm/episodeVm", () => ({
  buildEpisodeView: (x: any) => x,
}));

import LatestEpisodeView from "./LatestEpisodeView";

describe("LatestEpisodeView — edge cases for cameos/belief panel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("renders no cameos and no belief panel when there are zero agents", async () => {
    const vm: any = {
      id: "ep-empty",
      runId: "run-empty",
      index: 0,
      stageVersion: 1,
      days: [
        { index: 0, tensionScore: 0.1, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
      ],
      agents: [],
      tensionTrend: [0.1],
      story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
      _raw: {
        episode_id: "ep-empty",
        run_id: "run-empty",
        episode_index: 0,
        stage_version: 1,
        tension_trend: [0.1],
        days: [
          {
            day_index: 0,
            perception_mode: "n",
            tension_score: 0.1,
            total_incidents: 0,
            supervisor_activity: 0,
            agents: {},
            narrative: [],
          },
        ],
        agents: {},
        story_arc: null,
        narrative: [],
        long_memory: null,
        character_defs: null,
      },
    };

    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);
    render(<LatestEpisodeView />);

    const strip0 = await screen.findByTestId("day-storyboard-strip-0");
    expect(strip0).toBeTruthy();
    // No cameo cluster should render
    const cameoClusters = screen.queryAllByLabelText(/Agent cameos for Day 0/i);
    expect(cameoClusters.length).toBe(0);
    // No belief panel present
    expect(screen.queryByTestId("agent-belief-mini-panel")).toBeNull();
  });

  it("single-day episode: cameo toggles belief panel with fallback copy when no belief text", async () => {
    const vm: any = {
      id: "ep-single",
      runId: "run-single",
      index: 0,
      stageVersion: 1,
      days: [
        { index: 0, tensionScore: 0.25, totalIncidents: 2, perceptionMode: "n", supervisorActivity: 0 },
      ],
      agents: [],
      tensionTrend: [0.25],
      story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
      _raw: {
        episode_id: "ep-single",
        run_id: "run-single",
        episode_index: 0,
        stage_version: 1,
        tension_trend: [0.25],
        days: [
          {
            day_index: 0,
            perception_mode: "n",
            tension_score: 0.25,
            total_incidents: 2,
            supervisor_activity: 0,
            narrative: [],
            agents: {
              Ava: { name: "Ava", role: "ops", avg_stress: 0.4, guardrail_count: 0, context_count: 0, emotional_read: null, attribution_cause: null, narrative: [] },
            },
          },
        ],
        agents: {
          Ava: { name: "Ava", role: "ops", guardrail_total: 0, context_total: 0, stress_start: 0.2, stress_end: 0.4, trait_snapshot: null, visual: "", vibe: "", tagline: "" },
        },
        story_arc: null,
        narrative: [],
        long_memory: null,
        character_defs: null,
      },
    };

    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);
    render(<LatestEpisodeView />);

    const cameoCluster = await screen.findByLabelText(/Agent cameos for Day 0/i);
    const btn = within(cameoCluster).getByRole("button", { name: /View Ava's view of Day 0/i });
    fireEvent.click(btn);
    const panel = await screen.findByTestId("agent-belief-mini-panel");
    expect(panel).toBeTruthy();
    // Fallback copy since belief text is null
    expect(within(panel).getByText(/No explicit belief recorded for this day/i)).toBeTruthy();
    // Toggle off
    fireEvent.click(btn);
    expect(screen.queryByTestId("agent-belief-mini-panel")).toBeNull();
  });
});
