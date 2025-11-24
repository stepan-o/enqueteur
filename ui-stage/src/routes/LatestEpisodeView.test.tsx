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
      agents: [
        {
          name: "Ava",
          role: "ops",
          stressStart: 0.2,
          stressEnd: 0.1,
          stressDelta: -0.1,
          guardrailTotal: 0,
          contextTotal: 0,
          visual: "ava",
          vibe: "focused",
          tagline: "",
        },
      ],
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
