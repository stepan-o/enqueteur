// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import * as api from "../api/episodes";
import * as vm from "../vm/episodeVm";
import { useEpisodeLoader } from "./useEpisodeLoader";

function HookProbe() {
  const { episode, error, isLoading } = useEpisodeLoader();
  return (
    <div>
      <div>loading:{String(isLoading)}</div>
      <div>error:{error ?? ""}</div>
      <div>ep:{episode ? episode.id ?? "null-id" : "null"}</div>
    </div>
  );
}

describe("useEpisodeLoader", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("success path: sets episode and clears loading/error", async () => {
    const raw = { episode_id: "ep-123" } as any;
    const vmStub = { id: "ep-123", runId: "run-1", index: 0, stageVersion: 1, days: [], agents: [], tensionTrend: [] } as any;

    vi.spyOn(api, "getLatestEpisode").mockResolvedValue(raw);
    vi.spyOn(vm, "buildEpisodeView").mockReturnValue(vmStub);

    render(<HookProbe />);

    // Initial state shows loading true and no episode
    expect(screen.getByText(/loading:true/)).toBeTruthy();
    expect(screen.getByText(/ep:null/)).toBeTruthy();

    // After promise resolves
    expect(await screen.findByText(/loading:false/)).toBeTruthy();
    expect(screen.getByText(/error:/)).toBeTruthy();
    expect(screen.getByText(/ep:ep-123/)).toBeTruthy();
  });

  it("error path: sets error and leaves episode null", async () => {
    vi.spyOn(api, "getLatestEpisode").mockRejectedValue(new Error("boom"));
    // buildEpisodeView should not be called, but mock anyway to be safe
    vi.spyOn(vm, "buildEpisodeView").mockImplementation((x: any) => x);

    render(<HookProbe />);

    // Loading initially
    expect(screen.getByText(/loading:true/)).toBeTruthy();

    // After rejection
    expect(await screen.findByText(/loading:false/)).toBeTruthy();
    expect(screen.getByText(/error:boom/)).toBeTruthy();
    expect(screen.getByText(/ep:null/)).toBeTruthy();
  });
});
