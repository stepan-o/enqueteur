// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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

  it("renders the Episode Agents Overview with an agent name", async () => {
    const vm = {
      id: "ep-overview",
      runId: "run-overview",
      index: 0,
      stageVersion: 1,
      days: [],
      tensionTrend: [],
      agents: [],
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
  });
});
