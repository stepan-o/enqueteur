// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, within } from "@testing-library/react";

// Mock the episode loader hook per test to simulate edge states
vi.mock("../hooks/useEpisodeLoader", () => ({
  useEpisodeLoader: vi.fn(),
}));

import { useEpisodeLoader } from "../hooks/useEpisodeLoader";
import LatestEpisodeView from "./LatestEpisodeView";

describe("LatestEpisodeView loading/empty-state regression guard", () => {
  afterEach(() => {
    vi.resetAllMocks();
  });

  it("shows loading when isLoading=true and episode=null", async () => {
    (useEpisodeLoader as any).mockReturnValue({
      episode: null,
      error: null,
      isLoading: true,
    });

    const { container } = render(<LatestEpisodeView />);
    expect(within(container).getByText(/Loading latest StageEpisode…/)).toBeTruthy();
  });

  it("shows empty state when not loading and no episode", async () => {
    (useEpisodeLoader as any).mockReturnValue({
      episode: null,
      error: null,
      isLoading: false,
    });

    const { container } = render(<LatestEpisodeView />);
    expect(within(container).getByText(/No episode available\./)).toBeTruthy();
  });

  it("renders episode content when episode is present and loading is false", async () => {
    (useEpisodeLoader as any).mockReturnValue({
      episode: {
        id: "ep-ok",
        runId: "run-ok",
        index: 0,
        stageVersion: 1,
        days: [],
        agents: [],
        tensionTrend: [],
        story: {
          storyArc: null,
          longMemory: null,
          topLevelNarrative: [],
        },
        _raw: {
          episode_id: "ep-ok",
          run_id: "run-ok",
          episode_index: 0,
          stage_version: 1,
          tension_trend: [],
          days: [],
          agents: {},
          story_arc: null,
          narrative: [],
          long_memory: null,
          character_defs: null,
        },
      },
      error: null,
      isLoading: false,
    });

    const { container } = render(<LatestEpisodeView />);
    expect(await within(container).findByText(/ep-ok/)).toBeTruthy();
    // Ensure the loading text is not present within this render's container
    expect(within(container).queryByText(/Loading latest StageEpisode…/)).toBeNull();
  });
});
