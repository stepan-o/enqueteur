// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, within, fireEvent, waitFor } from "@testing-library/react";
import * as api from "../api/episodes";

// Mock buildEpisodeView to passthrough VM-shaped object
vi.mock("../vm/episodeVm", () => ({
  buildEpisodeView: (x: any) => x,
}));

import LatestEpisodeView from "./LatestEpisodeView";

describe("LatestEpisodeView — Episode Agents Overview integration", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the Episode Agents Overview with an agent name and shows EpisodeNavigator", async () => {
    const vm = {
      id: "ep-overview",
      runId: "run-overview",
      index: 0,
      stageVersion: 1,
      days: [],
      tensionTrend: [],
      agents: [],
      story: {
        storyArc: null,
        longMemory: null,
        topLevelNarrative: [],
      },
      _raw: {
        episode_id: "ep-overview",
        run_id: "run-overview",
        episode_index: 0,
        stage_version: 1,
        tension_trend: [],
        days: [],
        agents: {
          Ava: {
            name: "Ava",
            role: "ops",
            guardrail_total: 0,
            context_total: 0,
            stress_start: 0.2,
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
      },
    } as any;

    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);

    render(<LatestEpisodeView />);

    // Header appears
    const header = await screen.findByText(/Episode Agents Overview/i);
    expect(header).toBeTruthy();

    // Agent name appears somewhere in the view
    const agent = await screen.findByText(/Ava/);
    expect(agent).toBeTruthy();

    // EpisodeNavigator is present and shows the correct index
    const nav = await screen.findByTestId("episode-navigator");
    expect(nav).toBeTruthy();
    const current = await screen.findByTestId("episode-nav-current");
    expect(current.textContent || "").toMatch(/#0/);
  });

  it("wires daySummaries into TimelineStrip so a direction glyph renders", async () => {
    const vm = {
      id: "ep-timeline",
      runId: "run-timeline",
      index: 0,
      stageVersion: 1,
      days: [
        { index: 0, tensionScore: 0.1, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
        { index: 1, tensionScore: 0.3, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
      ],
      tensionTrend: [0.1, 0.3],
      agents: [],
      story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
      daySummaries: [
        { dayIndex: 0, tensionDirection: "unknown", tensionChange: null, primaryAgentName: null, primaryAgentStress: null, notableText: "" },
        { dayIndex: 1, tensionDirection: "up", tensionChange: 0.2, primaryAgentName: "Delta", primaryAgentStress: 0.84, notableText: "" },
      ],
      _raw: {
        episode_id: "ep-timeline",
        run_id: "run-timeline",
        episode_index: 0,
        stage_version: 1,
        tension_trend: [0.1, 0.3],
        days: [],
        agents: {},
        story_arc: null,
        narrative: [],
        long_memory: null,
        character_defs: null,
      },
    } as any;

    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);

    render(<LatestEpisodeView />);

    // Wait for timeline header to ensure view is mounted
    const header = await screen.findByText(/Timeline/i);
    expect(header).toBeTruthy();

    // Find the Day 1 button and assert it includes the up glyph in textContent
    const day1 = await screen.findByTestId("timeline-day-1");
    expect(day1.textContent || "").toMatch(/▲/);
  });

  it("renders Stage Map region labeled for selected day (Day 0) with correct tile tiers", async () => {
    const vm = {
      id: "ep-map",
      runId: "run-map",
      index: 0,
      stageVersion: 1,
      days: [
        { index: 0, tensionScore: 0.2, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 0 },
        { index: 1, tensionScore: 0.7, totalIncidents: 2, perceptionMode: "n", supervisorActivity: 0 },
      ],
      tensionTrend: [0.2, 0.7],
      agents: [],
      story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
      _raw: {
        episode_id: "ep-map",
        run_id: "run-map",
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
        agents: {},
        story_arc: null,
        narrative: [],
        long_memory: null,
        character_defs: null,
      },
    } as any;

    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm);

    render(<LatestEpisodeView />);

    // Wait for storyboard to mount to ensure view is ready
    await screen.findByTestId("day-storyboard-strip-0");

    // Stage Map group should be present; tiles should reflect low tier for day 0
    const mapGroups = await screen.findAllByTestId("stage-map-group");
    const mapGroup = mapGroups[0];
    const tiles = within(mapGroup).getAllByRole("img");
    tiles.forEach((el) => expect(el.getAttribute("data-tension-tier")).toBe("low"));
  });
});
