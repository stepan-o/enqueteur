// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, within } from "@testing-library/react";
import * as api from "../api/episodes";

// Provide VM passthrough so we can inject EpisodeViewModel-like object
vi.mock("../vm/episodeVm", () => ({
  buildEpisodeView: (x: any) => x,
}));

import LatestEpisodeView from "./LatestEpisodeView";

function makeVm() {
  const vm: any = {
    id: "ep-belief",
    runId: "run-belief",
    index: 0,
    stageVersion: 1,
    days: [
      { index: 0, tensionScore: 0.2, totalIncidents: 1, perceptionMode: "n", supervisorActivity: 0 },
      { index: 1, tensionScore: 0.4, totalIncidents: 0, perceptionMode: "n", supervisorActivity: 1 },
    ],
    agents: [],
    tensionTrend: [0.2, 0.4],
    story: { storyArc: null, longMemory: null, topLevelNarrative: [] },
    _raw: {
      episode_id: "ep-belief",
      run_id: "run-belief",
      episode_index: 0,
      stage_version: 1,
      tension_trend: [0.2, 0.4],
      days: [
        {
          day_index: 0,
          perception_mode: "n",
          tension_score: 0.2,
          total_incidents: 1,
          supervisor_activity: 0,
          narrative: [],
          agents: {
            Ava: { name: "Ava", role: "ops", avg_stress: 0.6, guardrail_count: 0, context_count: 0, emotional_read: null, attribution_cause: "network outage", narrative: [] },
            Bob: { name: "Bob", role: "tech", avg_stress: 0.3, guardrail_count: 0, context_count: 0, emotional_read: null, attribution_cause: null, narrative: [] },
          },
        },
        {
          day_index: 1,
          perception_mode: "n",
          tension_score: 0.4,
          total_incidents: 0,
          supervisor_activity: 1,
          narrative: [],
          agents: {
            Ava: { name: "Ava", role: "ops", avg_stress: 0.5, guardrail_count: 0, context_count: 0, emotional_read: null, attribution_cause: null, narrative: [] },
          },
        },
      ],
      agents: {
        Ava: { name: "Ava", role: "operator", guardrail_total: 0, context_total: 0, stress_start: 0.1, stress_end: 0.6, trait_snapshot: null, visual: "", vibe: "", tagline: "" },
        Bob: { name: "Bob", role: "support", guardrail_total: 0, context_total: 0, stress_start: 0.1, stress_end: 0.3, trait_snapshot: null, visual: "", vibe: "", tagline: "" },
      },
      story_arc: null,
      narrative: [],
      long_memory: null,
      character_defs: null,
    },
  };
  return vm;
}

describe("LatestEpisodeView — AgentBeliefMiniPanel interaction", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("opens on cameo click without scrolling, toggles on second click, and clears on day change; strip click scrolls", async () => {
    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(makeVm());
    render(<LatestEpisodeView />);

    // Wait for Day 0 strip
    const strip0 = await screen.findByTestId("day-storyboard-strip-0");
    expect(strip0).toBeTruthy();

    // Polyfill and spy on scrollIntoView to detect (no) scrolling
    const originalScroll = (Element.prototype as any).scrollIntoView;
    const scrollSpy = vi.fn();
    (Element.prototype as any).scrollIntoView = scrollSpy;

    // Find cameo button for Ava on Day 0
    const cameoCluster = await screen.findByLabelText(/Agent cameos for Day 0/i);
    const btn = within(cameoCluster).getByRole("button", { name: /View Ava's view of Day 0/i });
    fireEvent.click(btn);

    // Panel opens with belief text (scope query within the panel to avoid duplicates elsewhere)
    const panel = await screen.findByTestId("agent-belief-mini-panel");
    expect(panel).toBeTruthy();
    expect(within(panel).getByText(/network outage/i)).toBeTruthy();

    // Cameo click should NOT trigger scrolling
    expect(scrollSpy).not.toHaveBeenCalled();

    // Second click toggles off
    fireEvent.click(btn);
    expect(screen.queryByTestId("agent-belief-mini-panel")).toBeNull();

    // Click again to open, then change day via strip 1 and ensure it clears
    fireEvent.click(btn);
    const strip1 = await screen.findByTestId("day-storyboard-strip-1");
    fireEvent.click(strip1);
    expect(screen.queryByTestId("agent-belief-mini-panel")).toBeNull();

    // Strip click should trigger scrolling at least once
    expect(scrollSpy).toHaveBeenCalled();

    // restore original scrollIntoView if present
    (Element.prototype as any).scrollIntoView = originalScroll;
  });
});
