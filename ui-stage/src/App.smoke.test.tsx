// @vitest-environment jsdom
// ui-stage/src/App.smoke.test.tsx
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import * as api from "./api/episodes";

// The App builds a VM from the API result. For this smoke test, we mock
// getLatestEpisode to return a VM-shaped object and make buildEpisodeView
// act as an identity function so the App receives the VM as-is. This keeps
// the test focused on app-level rendering rather than transformation.
vi.mock("./vm/episodeVm", () => {
  return {
    buildEpisodeView: (x: any) => x,
  };
});

import LatestEpisodeView from "./routes/LatestEpisodeView";

describe("App smoke test with mocked API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading then populates with episode info", async () => {
    const vm = {
      id: "ep-smoke",
      runId: "run-smoke",
      index: 0,
      stageVersion: 1,
      days: [],
      agents: [],
      tensionTrend: [0.1, 0.3],
    };

    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(vm as unknown as any);

    render(<LatestEpisodeView />);

    // Should eventually show the episode id from the mocked VM
    const epEl = await screen.findByText(/ep-smoke/);
    expect(epEl).toBeTruthy();
    expect(screen.getByText(/run-smoke/)).toBeTruthy();
    expect(screen.getByText(/Stage Version/)).toBeTruthy();
  });
});
